import uuid

from sqlalchemy import bindparam, delete, text
from sqlalchemy.orm import Session

from models.static_source_model import StaticSource

# The one place the static-source rule lives: a detection without a FIRMS "type" is static when
# a known source is in its 0.01° cell or one of the 8 around it. Integer casts keep the lookup on
# the primary key index (floor returns double). Only rows whose flag changes are written.
NEAR_STATIC_SOURCE = """
    EXISTS (
        SELECT 1 FROM static_sources s
        WHERE s.latitude_key BETWEEN floor(f.latitude * 100 + 0.5)::integer - 1
                                 AND floor(f.latitude * 100 + 0.5)::integer + 1
          AND s.longitude_key BETWEEN floor(f.longitude * 100 + 0.5)::integer - 1
                                  AND floor(f.longitude * 100 + 0.5)::integer + 1
    )
"""
MARK_ALL = text(
    f"UPDATE fire_detections f SET is_static_source = {NEAR_STATIC_SOURCE} "
    f"WHERE f.fire_type IS NULL AND f.is_static_source IS DISTINCT FROM {NEAR_STATIC_SOURCE}"
)
MARK_RUNS = text(
    f"UPDATE fire_detections f SET is_static_source = {NEAR_STATIC_SOURCE} "
    f"WHERE f.fire_type IS NULL AND f.ingestion_run_id IN :run_ids "
    f"AND f.is_static_source IS DISTINCT FROM {NEAR_STATIC_SOURCE}"
).bindparams(bindparam("run_ids", expanding=True))

# One statement for hundreds of thousands of rows, instead of a row-by-row insert.
INSERT_KEYS = text(
    "INSERT INTO static_sources (latitude_key, longitude_key) "
    "SELECT * FROM unnest(CAST(:latitude_keys AS integer[]), CAST(:longitude_keys AS integer[]))"
)


def replace_all(session: Session, keys: set[tuple[int, int]]) -> int:
    session.execute(delete(StaticSource))
    if keys:
        latitude_keys, longitude_keys = map(list, zip(*keys, strict=True))
        session.execute(
            INSERT_KEYS, {"latitude_keys": latitude_keys, "longitude_keys": longitude_keys}
        )
    session.commit()
    return len(keys)


def mark_detections(session: Session, run_ids: list[uuid.UUID] | None = None) -> int:
    """Set is_static_source on detections without a FIRMS type (all, or only these runs').
    Returns how many rows changed."""
    if run_ids is None:
        changed = session.execute(MARK_ALL).rowcount
    else:
        changed = session.execute(MARK_RUNS, {"run_ids": run_ids}).rowcount
    session.commit()
    return changed
