"""GET /fires/live: the last 7 days of near-real-time fires in the website's live.json shape.

Building it reads every detection of the week (hundreds of thousands of rows, a few seconds),
so the refresh thread builds it right after each fetch and requests only read the encoded,
already gzipped bytes. A request rebuilds only when a newer fetch finished elsewhere (e.g. a
manual POST /ingestions) or nothing is built yet.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from configurations.database_config import get_session_factory
from constants.ingestion_constants import IngestionKind
from repositories import fire_detection_repository, ingestion_run_repository
from utilities.cached_body_util import CachedBody, VersionedCache, cached_json
from utilities.live_payload_util import build_live_payload

LIVE_WINDOW = timedelta(days=7)

cache = VersionedCache()


def build(session: Session) -> CachedBody:
    now = datetime.now(UTC)
    rows = fire_detection_repository.near_real_time_rows(session, now - LIVE_WINDOW)
    return cached_json(build_live_payload(rows, now))


def get_live_body(session: Session) -> CachedBody:
    # Keyed on the last near-real-time fetch it includes.
    fetched_at = ingestion_run_repository.last_success_finished_at(
        session, IngestionKind.NEAR_REAL_TIME
    )
    return cache.get("live", fetched_at, lambda: build(session))


def rebuild() -> None:
    """Called by the refresh thread after each fetch, so requests don't wait for a build."""
    with get_session_factory()() as session:
        get_live_body(session)
