from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from configurations.environment_config import environment


def get_database_password() -> str:
    return Path(environment.POSTGRES_PASSWORD_FILE).expanduser().read_text().strip()


def get_database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=environment.POSTGRES_USER,
        password=get_database_password(),
        host=environment.POSTGRES_HOST,
        port=environment.POSTGRES_PORT,
        database=environment.POSTGRES_DB,
    )


@cache
def get_database_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


@cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_database_engine(), expire_on_commit=False)


def get_database_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed afterwards."""
    with get_session_factory()() as session:
        yield session


DatabaseSession = Annotated[Session, Depends(get_database_session)]
