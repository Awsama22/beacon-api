"""Fetches FIRMS CSVs and stores them in fire_detections. Each source fetch is one ingestion run,
created right away and filled in by a background task."""

import csv
import itertools
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from configurations.database_config import get_session_factory
from configurations.environment_config import environment
from configurations.logger_config import logger
from constants.firms_constants import ARCHIVE_FILES, NEAR_REAL_TIME_FILES, FirmsSource
from constants.ingestion_constants import INSERT_BATCH_SIZE, IngestionKind, IngestionStatus
from models.ingestion_run_model import IngestionRun
from repositories import (
    fire_detection_repository,
    ingestion_run_repository,
    static_source_repository,
)
from utilities.api_error_util import ApiError
from utilities.firms_parser_util import parse_detection
from validators.ingestion_validator import (
    ArchiveIngestionRequest,
    AreaIngestionRequest,
    NearRealTimeIngestionRequest,
)

MAX_PARALLEL_DOWNLOADS = 4
Plan = tuple[str, dict, str]  # source, parameters stored on the run, URL to fetch
PendingRun = tuple[uuid.UUID, str]  # run id, URL to fetch


def near_real_time_url(source: FirmsSource, period: str) -> str:
    path = NEAR_REAL_TIME_FILES[source].format(period=period)
    return f"{environment.FIRMS_BASE_URL}/data/active_fire/{path}"


def archive_url(source: FirmsSource, country: str, year: int) -> str:
    path = ARCHIVE_FILES[source].format(year=year, country=country)
    return f"{environment.FIRMS_BASE_URL}/data/country/{path}"


def area_url(request: AreaIngestionRequest) -> str:
    box = ",".join(map(str, request.bbox.as_tuple()))
    url = (
        f"{environment.FIRMS_BASE_URL}/api/area/csv/{environment.FIRMS_MAP_KEY}/{request.source}/"
        f"{box}/{request.day_range}"
    )
    return f"{url}/{request.start_date.isoformat()}" if request.start_date else url


def plan_near_real_time(request: NearRealTimeIngestionRequest) -> list[Plan]:
    return [
        (source, {"period": request.period}, near_real_time_url(source, request.period))
        for source in request.sources
    ]


def plan_area(request: AreaIngestionRequest) -> list[Plan]:
    if not environment.FIRMS_MAP_KEY:
        raise ApiError(400, "FIRMS_MAP_KEY is not set, so the FIRMS Area API cannot be used")
    parameters = request.model_dump(mode="json", exclude={"source"})
    return [(request.source, parameters, area_url(request))]


def plan_archive(request: ArchiveIngestionRequest) -> list[Plan]:
    parameters = request.model_dump(mode="json", exclude={"source"})
    url = archive_url(request.source, request.country, request.year)
    return [(request.source, parameters, url)]


def create_runs(
    session: Session, kind: IngestionKind, plans: list[Plan]
) -> tuple[list[IngestionRun], list[PendingRun]]:
    """One run per source, recorded as running; returns the runs and the work to do."""
    runs = [
        ingestion_run_repository.create_run(session, kind, source, parameters)
        for source, parameters, _ in plans
    ]
    return runs, [(run.id, url) for run, (_, _, url) in zip(runs, plans, strict=True)]


def start_ingestion(
    session: Session, background_tasks: BackgroundTasks, kind: IngestionKind, plans: list[Plan]
) -> list[IngestionRun]:
    """Create the runs now; fetch and store them after the response is sent."""
    runs, pending = create_runs(session, kind, plans)
    background_tasks.add_task(run_pending, pending)
    return runs


def stream_rows(url: str) -> Iterator[dict[str, str]]:
    with httpx.stream(
        "GET", url, timeout=environment.DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True
    ) as response:
        if response.status_code == 404:
            raise ValueError("FIRMS has no file for this request (404)")
        response.raise_for_status()
        lines = response.iter_lines()
        header = next(lines, "")
        if "latitude" not in header:
            # The Area API answers errors (bad key, too many requests) as plain text.
            raise ValueError(f"FIRMS did not return fire data: {header[:200]}")
        yield from csv.DictReader(itertools.chain([header], lines))


def store_rows(session: Session, run: IngestionRun, url: str) -> tuple[int, int]:
    source = FirmsSource(run.source)
    rows_read = rows_stored = 0
    batch: list[dict] = []
    for row in stream_rows(url):
        rows_read += 1
        detection = parse_detection(row, source)
        if detection:
            batch.append({**detection, "ingestion_run_id": run.id})
        if len(batch) >= INSERT_BATCH_SIZE:
            rows_stored += fire_detection_repository.insert_detections(session, batch)
            batch = []
    rows_stored += fire_detection_repository.insert_detections(session, batch)
    return rows_read, rows_stored


def redact(text: str) -> str:
    key = environment.FIRMS_MAP_KEY
    return text.replace(key, "***") if key else text


def run_one(pending_run: PendingRun) -> None:
    run_id, url = pending_run
    with get_session_factory()() as session:
        run = ingestion_run_repository.get_run(session, run_id)
        if run is None:
            return
        try:
            rows_read, rows_stored = store_rows(session, run, url)
            status, error = IngestionStatus.SUCCEEDED, None
        except Exception as exception:
            session.rollback()
            rows_read = rows_stored = 0
            status = IngestionStatus.FAILED
            error = redact(
                f"{type(exception).__name__}: {(str(exception).splitlines() or [''])[0][:500]}"
            )
            logger.warning("Ingestion %s (%s) failed: %s", run.id, run.source, error)
        ingestion_run_repository.finish_run(session, run, status, rows_read, rows_stored, error)
        logger.info(
            "Ingestion %s (%s): %s, %s read, %s new",
            run.id,
            run.source,
            status,
            rows_read,
            rows_stored,
        )


def run_pending(pending: list[PendingRun]) -> None:
    """Background task: fetch each source in its own thread (sources never share rows), then mark
    the new rows that sit on known static heat sources (near-real-time files have no FIRMS type)."""
    with ThreadPoolExecutor(max_workers=min(len(pending), MAX_PARALLEL_DOWNLOADS)) as pool:
        list(pool.map(run_one, pending))
    with get_session_factory()() as session:
        static_source_repository.mark_detections(session, [run_id for run_id, _ in pending])
