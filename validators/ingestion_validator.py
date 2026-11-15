from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, RootModel, model_validator

from constants.firms_constants import (
    ARCHIVE_FILES,
    NEAR_REAL_TIME_SOURCES,
    FirmsSource,
)
from validators.bounding_box_validator import BoundingBox


class NearRealTimeIngestionRequest(BaseModel):
    """Global near-real-time files, no key needed."""

    sources: list[FirmsSource] = Field(default_factory=lambda: list(NEAR_REAL_TIME_SOURCES))
    period: Literal["24h", "48h", "7d"] = "24h"

    @model_validator(mode="after")
    def check_sources(self):
        wrong = [s for s in self.sources if s not in NEAR_REAL_TIME_SOURCES]
        if wrong or not self.sources:
            raise ValueError(f"sources must be some of {[str(s) for s in NEAR_REAL_TIME_SOURCES]}")
        self.sources = list(dict.fromkeys(self.sources))  # each source fetched once
        return self


class AreaIngestionRequest(BaseModel):
    """FIRMS Area API (needs FIRMS_MAP_KEY): one source, one box, 1 to 10 days."""

    source: FirmsSource
    bbox: BoundingBox
    day_range: int = Field(default=1, ge=1, le=10)
    start_date: date | None = None


class ArchiveIngestionRequest(BaseModel):
    """FIRMS yearly country archive, no key needed."""

    source: FirmsSource = FirmsSource.VIIRS_SNPP_SP
    country: str = Field(pattern=r"^[A-Z][A-Za-z_]+$", examples=["United_Arab_Emirates"])
    year: int = Field(ge=2000, le=2100)

    @model_validator(mode="after")
    def check_source(self):
        if self.source not in ARCHIVE_FILES:
            raise ValueError(f"source must be one of {[str(s) for s in ARCHIVE_FILES]}")
        return self


class StaticSourcesRequest(RootModel[list[tuple[float, float]]]):
    """[[latitude, longitude], ...] of static heat sources, like the website's flares.json."""

    root: list[tuple[float, float]] = Field(max_length=2_000_000)
