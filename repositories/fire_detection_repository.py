from datetime import UTC, datetime, timedelta
from math import cos, radians

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from constants.firms_constants import CONFIDENCE_RANK, NEAR_REAL_TIME_SOURCES
from models.fire_detection_model import FireDetection
from validators.fire_validator import FireAreaQuery, FireFilters, FireNearQuery

EARTH_RADIUS_KM = 6371.0
KM_PER_DEGREE_LATITUDE = 111.0


def insert_detections(session: Session, rows: list[dict]) -> int:
    """Insert a batch, skipping detections already stored. Returns how many were new."""
    if not rows:
        return 0
    query = (
        insert(FireDetection)
        .on_conflict_do_nothing(constraint="uq_fire_detection")
        .returning(FireDetection.id)
    )
    # Passing rows separately lets SQLAlchemy split them under PostgreSQL's parameter limit.
    stored = len(session.execute(query, rows).all())
    session.commit()
    return stored


def apply_filters(query: Select, filters: FireFilters) -> Select:
    minimum = CONFIDENCE_RANK[filters.min_confidence]
    levels = [level for level, rank in CONFIDENCE_RANK.items() if rank >= minimum]
    query = query.where(FireDetection.confidence_level.in_(levels))
    if filters.sensor:
        query = query.where(FireDetection.sensor == filters.sensor)
    if not filters.include_static:
        query = query.where(FireDetection.is_static_source.is_not(True))
    if filters.start:
        query = query.where(FireDetection.acquired_at >= filters.start)
    if filters.end:
        query = query.where(FireDetection.acquired_at < filters.end)
    return query


def in_box(query: Select, west: float, south: float, east: float, north: float) -> Select:
    return query.where(
        FireDetection.longitude.between(west, east), FireDetection.latitude.between(south, north)
    )


def distance_km(latitude: float, longitude: float):
    """Haversine distance from a point to each detection, in SQL."""
    d_latitude = func.radians(FireDetection.latitude - latitude)
    d_longitude = func.radians(FireDetection.longitude - longitude)
    a = func.power(func.sin(d_latitude / 2), 2) + func.cos(func.radians(latitude)) * func.cos(
        func.radians(FireDetection.latitude)
    ) * func.power(func.sin(d_longitude / 2), 2)
    return 2 * EARTH_RADIUS_KM * func.asin(func.sqrt(func.least(a, 1.0)))


def find_in_box(session: Session, query: FireAreaQuery) -> list[FireDetection]:
    statement = apply_filters(in_box(select(FireDetection), *query.as_tuple()), query)
    statement = statement.order_by(FireDetection.acquired_at.desc())
    return list(session.scalars(statement.limit(query.limit).offset(query.offset)))


def find_near(session: Session, query: FireNearQuery) -> list[tuple[FireDetection, float]]:
    latitude, longitude = query.latitude, query.longitude
    d_lat = query.radius_km / KM_PER_DEGREE_LATITUDE
    d_lon = min(180.0, d_lat / max(0.01, abs(cos(radians(latitude)))))
    distance = distance_km(latitude, longitude).label("distance_km")
    statement = in_box(
        select(FireDetection, distance),
        longitude - d_lon,
        latitude - d_lat,
        longitude + d_lon,
        latitude + d_lat,
    )
    statement = apply_filters(statement, query).where(distance <= query.radius_km)
    if query.hours:
        since = datetime.now(UTC) - timedelta(hours=query.hours)
        statement = statement.where(FireDetection.acquired_at >= since)
    return session.execute(statement.order_by(distance).limit(query.limit)).tuples().all()


def monthly_counts(session: Session, query: FireAreaQuery) -> list[tuple[datetime, str, str, int]]:
    month = func.date_trunc("month", FireDetection.acquired_at).label("month")
    statement = select(month, FireDetection.sensor, FireDetection.source, func.count())
    statement = apply_filters(in_box(statement, *query.as_tuple()), query)
    statement = statement.group_by(month, FireDetection.sensor, FireDetection.source)
    return session.execute(statement.order_by(month)).tuples().all()


def near_real_time_rows(session: Session, since: datetime):
    """Columns the live payload needs, streamed, for near-real-time detections since a time."""
    query = (
        select(
            FireDetection.latitude,
            FireDetection.longitude,
            FireDetection.frp,
            FireDetection.source,
            FireDetection.satellite,
            FireDetection.acquired_at,
            FireDetection.confidence_level,
            FireDetection.day_night,
            FireDetection.is_static_source,
        )
        .where(FireDetection.source.in_(NEAR_REAL_TIME_SOURCES))
        .order_by(FireDetection.source, FireDetection.acquired_at)
        .execution_options(yield_per=20000)
    )
    # Nominal and high confidence, static sources included (the payload lists them apart).
    query = apply_filters(query, FireFilters(include_static=True, start=since))
    return session.execute(query).tuples()


def delete_near_real_time_before(session: Session, cutoff: datetime) -> int:
    query = delete(FireDetection).where(
        FireDetection.source.in_(NEAR_REAL_TIME_SOURCES), FireDetection.acquired_at < cutoff
    )
    deleted = session.execute(query).rowcount
    session.commit()
    return deleted
