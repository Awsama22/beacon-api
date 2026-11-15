from datetime import datetime

from pydantic import BaseModel, Field

from constants.firms_constants import ConfidenceLevel, Sensor
from validators.bounding_box_validator import BoundingBox


class FireFilters(BaseModel):
    """Shared fire query filters. Static sources and low confidence are left out by default."""

    sensor: Sensor | None = None
    min_confidence: ConfidenceLevel = ConfidenceLevel.NOMINAL
    include_static: bool = False
    start: datetime | None = None
    end: datetime | None = None
    limit: int = Field(default=5000, ge=1, le=50000)


class FireAreaQuery(FireFilters, BoundingBox):
    offset: int = Field(default=0, ge=0)


class FireNearQuery(FireFilters):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=50, gt=0, le=1500)
    hours: int | None = Field(default=168, ge=1, le=24 * 366 * 30)
