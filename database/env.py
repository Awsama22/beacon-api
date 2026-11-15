from alembic import context
from sqlalchemy import Connection

import configurations.logger_config  # noqa: F401  (shows Alembic's progress logs)
from configurations.database_config import get_database_engine, get_database_url
from models import BaseModel

target_metadata = BaseModel.metadata


def run_migrations_offline() -> None:
    """Write the SQL to stdout instead of running it (alembic upgrade --sql)."""
    context.configure(
        url=get_database_url().render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with get_database_engine().connect() as connection:
        run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
