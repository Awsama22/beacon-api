from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models.dataset_model import Dataset


def get_payload(session: Session, name: str) -> Any | None:
    return session.scalar(select(Dataset.payload).where(Dataset.name == name))


def last_updated_at(session: Session) -> datetime | None:
    """Changes whenever any dataset is imported; the cached response bodies are keyed on it."""
    return session.scalar(select(func.max(Dataset.updated_at)))


def save(session: Session, name: str, payload: Any) -> None:
    query = insert(Dataset).values(name=name, payload=payload)
    query = query.on_conflict_do_update(
        index_elements=[Dataset.name], set_={"payload": payload, "updated_at": func.now()}
    )
    session.execute(query)
