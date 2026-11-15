import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from constants.ingestion_constants import IngestionStatus
from models.ingestion_run_model import IngestionRun


def create_run(session: Session, kind: str, source: str, parameters: dict) -> IngestionRun:
    run = IngestionRun(
        kind=kind, source=source, parameters=parameters, status=IngestionStatus.RUNNING
    )
    session.add(run)
    session.commit()
    return run


def get_run(session: Session, run_id: uuid.UUID) -> IngestionRun | None:
    return session.get(IngestionRun, run_id)


def list_runs(session: Session, limit: int) -> list[IngestionRun]:
    query = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    return list(session.scalars(query))


def finish_run(
    session: Session,
    run: IngestionRun,
    status: IngestionStatus,
    rows_read: int,
    rows_stored: int,
    error: str | None = None,
) -> None:
    run.status = status
    run.rows_read = rows_read
    run.rows_stored = rows_stored
    run.error = error
    run.finished_at = func.now()
    session.commit()


def last_success_by_source(session: Session) -> dict[str, IngestionRun]:
    query = (
        select(IngestionRun)
        .where(IngestionRun.status == IngestionStatus.SUCCEEDED)
        .order_by(IngestionRun.source, IngestionRun.finished_at.desc())
        .distinct(IngestionRun.source)
    )
    return {run.source: run for run in session.scalars(query)}


def last_success_finished_at(session: Session, kind: str) -> datetime | None:
    query = select(func.max(IngestionRun.finished_at)).where(
        IngestionRun.kind == kind, IngestionRun.status == IngestionStatus.SUCCEEDED
    )
    return session.scalar(query)
