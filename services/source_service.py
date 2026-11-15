from sqlalchemy.orm import Session

from configurations.environment_config import environment
from constants.firms_constants import ARCHIVE_FILES, NEAR_REAL_TIME_FILES, FirmsSource, sensor_of
from repositories import ingestion_run_repository
from utilities.date_util import iso_or_none


def list_sources(session: Session) -> list[dict]:
    """Every FIRMS source the API can fetch, how, and when it last succeeded."""
    last = ingestion_run_repository.last_success_by_source(session)
    sources = []
    for source in FirmsSource:
        run = last.get(source)
        sources.append(
            {
                "source": source,
                "sensor": sensor_of(source),
                "near_real_time_file": source in NEAR_REAL_TIME_FILES,
                "yearly_archive": source in ARCHIVE_FILES,
                "area_api": bool(environment.FIRMS_MAP_KEY),
                "last_success_at": iso_or_none(run.finished_at) if run else None,
                "last_rows_stored": run.rows_stored if run else None,
            }
        )
    return sources
