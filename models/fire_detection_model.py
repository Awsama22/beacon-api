import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class FireDetection(BaseModel):
    """One satellite hot spot from NASA FIRMS (MODIS or VIIRS)."""

    __tablename__ = "fire_detections"
    __table_args__ = (
        # The same detection fetched twice (overlapping 24h/7d files or API calls) is stored once.
        UniqueConstraint(
            "source", "latitude", "longitude", "acquired_at", name="uq_fire_detection"
        ),
        Index("ix_fire_detections_latitude_longitude", "latitude", "longitude"),
        # Live payload and retention: near-real-time sources over a time window.
        Index("ix_fire_detections_source_acquired_at", "source", "acquired_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32))
    sensor: Mapped[str] = mapped_column(String(8))
    satellite: Mapped[str] = mapped_column(String(8))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    brightness: Mapped[float | None] = mapped_column(Float)
    frp: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(8))
    confidence_level: Mapped[str] = mapped_column(String(8))
    day_night: Mapped[str | None] = mapped_column(String(1))
    fire_type: Mapped[int | None] = mapped_column(SmallInteger)
    is_static_source: Mapped[bool | None] = mapped_column(Boolean)
    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
