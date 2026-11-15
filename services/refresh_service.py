"""Keeps near-real-time fires current: fetches FIRMS every LIVE_REFRESH_MINUTES in a background
thread, picking the 24h, 48h or 7d files to cover the gap since the last successful fetch, then
rebuilds the /fires/live body and deletes near-real-time detections older than
NRT_RETENTION_DAYS.

This needs a long-running server (uvicorn). On a serverless host the thread would not survive
between requests; there, call refresh_once from a scheduled job instead.
"""

import threading
from datetime import UTC, datetime, timedelta

from configurations.database_config import get_session_factory
from configurations.environment_config import environment
from configurations.logger_config import logger
from constants.ingestion_constants import IngestionKind
from repositories import fire_detection_repository, ingestion_run_repository
from services import ingestion_service, live_fire_service
from validators.ingestion_validator import NearRealTimeIngestionRequest


def period_for(gap: timedelta | None) -> str:
    """The smallest FIRMS file that still covers the gap (with a few hours of margin)."""
    if gap is None or gap > timedelta(hours=44):
        return "7d"
    return "48h" if gap > timedelta(hours=20) else "24h"


def time_since_last_fetch() -> timedelta | None:
    with get_session_factory()() as session:
        last = ingestion_run_repository.last_success_finished_at(
            session, IngestionKind.NEAR_REAL_TIME
        )
    return datetime.now(UTC) - last if last else None


def refresh_once(period: str) -> None:
    request = NearRealTimeIngestionRequest(period=period)
    with get_session_factory()() as session:
        _, pending = ingestion_service.create_runs(
            session, IngestionKind.NEAR_REAL_TIME, ingestion_service.plan_near_real_time(request)
        )
    ingestion_service.run_pending(pending)
    live_fire_service.rebuild()
    cutoff = datetime.now(UTC) - timedelta(days=environment.NRT_RETENTION_DAYS)
    with get_session_factory()() as session:
        deleted = fire_detection_repository.delete_near_real_time_before(session, cutoff)
    logger.info("Live refresh (%s) done; %s old near-real-time detections deleted", period, deleted)


def refresh_loop(stop: threading.Event) -> None:
    interval = timedelta(minutes=environment.LIVE_REFRESH_MINUTES)
    while not stop.is_set():
        wait = interval
        try:
            gap = time_since_last_fetch()
            if gap is None or gap >= interval:
                refresh_once(period_for(gap))
            else:
                wait = interval - gap
                live_fire_service.rebuild()  # warm the cache after a restart
        except Exception:
            logger.exception("Live refresh failed; retrying in %s", interval)
        stop.wait(wait.total_seconds())


def start() -> threading.Event:
    """Start the refresh thread unless LIVE_REFRESH_MINUTES is 0. Set the event to stop it."""
    stop = threading.Event()
    if environment.LIVE_REFRESH_MINUTES > 0:
        threading.Thread(
            target=refresh_loop, args=(stop,), name="live-refresh", daemon=True
        ).start()
        logger.info("Live refresh every %s minutes", environment.LIVE_REFRESH_MINUTES)
    return stop
