import uuid
from typing import Annotated

from fastapi import BackgroundTasks, Query

from configurations.database_config import DatabaseSession
from constants.ingestion_constants import IngestionKind
from models.ingestion_run_model import IngestionRun
from repositories import ingestion_run_repository
from services import ingestion_service, static_source_service
from utilities.api_error_util import ApiError
from utilities.api_response_util import success_response
from utilities.date_util import iso_or_none
from validators.ingestion_validator import (
    ArchiveIngestionRequest,
    AreaIngestionRequest,
    NearRealTimeIngestionRequest,
    StaticSourcesRequest,
)


def serialize_run(run: IngestionRun) -> dict:
    return {
        "id": str(run.id),
        "kind": run.kind,
        "source": run.source,
        "parameters": run.parameters,
        "status": run.status,
        "rows_read": run.rows_read,
        "rows_stored": run.rows_stored,
        "error": run.error,
        "started_at": iso_or_none(run.started_at),
        "finished_at": iso_or_none(run.finished_at),
    }


def started(runs: list[IngestionRun]) -> dict:
    return success_response({"runs": [serialize_run(run) for run in runs]})


def ingest_near_real_time(
    body: NearRealTimeIngestionRequest, background_tasks: BackgroundTasks, session: DatabaseSession
) -> dict:
    plans = ingestion_service.plan_near_real_time(body)
    return started(
        ingestion_service.start_ingestion(
            session, background_tasks, IngestionKind.NEAR_REAL_TIME, plans
        )
    )


def ingest_area(
    body: AreaIngestionRequest, background_tasks: BackgroundTasks, session: DatabaseSession
) -> dict:
    plans = ingestion_service.plan_area(body)
    return started(
        ingestion_service.start_ingestion(session, background_tasks, IngestionKind.AREA, plans)
    )


def ingest_archive(
    body: ArchiveIngestionRequest, background_tasks: BackgroundTasks, session: DatabaseSession
) -> dict:
    plans = ingestion_service.plan_archive(body)
    return started(
        ingestion_service.start_ingestion(session, background_tasks, IngestionKind.ARCHIVE, plans)
    )


def list_ingestions(
    session: DatabaseSession, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> dict:
    runs = ingestion_run_repository.list_runs(session, limit)
    return success_response([serialize_run(run) for run in runs])


def get_ingestion(run_id: uuid.UUID, session: DatabaseSession) -> dict:
    run = ingestion_run_repository.get_run(session, run_id)
    if run is None:
        raise ApiError(404, "Ingestion run not found")
    return success_response(serialize_run(run))


def replace_static_sources(body: StaticSourcesRequest, session: DatabaseSession) -> dict:
    return success_response(static_source_service.replace_static_sources(session, body.root))
