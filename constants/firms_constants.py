from enum import StrEnum


class Sensor(StrEnum):
    MODIS = "MODIS"
    VIIRS = "VIIRS"


class FirmsSource(StrEnum):
    """FIRMS source names, as used by the FIRMS Area API."""

    MODIS_NRT = "MODIS_NRT"
    MODIS_SP = "MODIS_SP"
    VIIRS_SNPP_NRT = "VIIRS_SNPP_NRT"
    VIIRS_SNPP_SP = "VIIRS_SNPP_SP"
    VIIRS_NOAA20_NRT = "VIIRS_NOAA20_NRT"
    VIIRS_NOAA20_SP = "VIIRS_NOAA20_SP"
    VIIRS_NOAA21_NRT = "VIIRS_NOAA21_NRT"


# Free global near-real-time CSVs (no key), under {FIRMS_BASE_URL}/data/active_fire/.
# "{period}" is 24h, 48h or 7d.
NEAR_REAL_TIME_FILES = {
    FirmsSource.MODIS_NRT: "modis-c6.1/csv/MODIS_C6_1_Global_{period}.csv",
    FirmsSource.VIIRS_SNPP_NRT: "suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_{period}.csv",
    FirmsSource.VIIRS_NOAA20_NRT: "noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_{period}.csv",
    FirmsSource.VIIRS_NOAA21_NRT: "noaa-21-viirs-c2/csv/J2_VIIRS_C2_Global_{period}.csv",
}
NEAR_REAL_TIME_SOURCES = list(NEAR_REAL_TIME_FILES)

# Free yearly country archives (no key), under {FIRMS_BASE_URL}/data/country/.
ARCHIVE_FILES = {
    FirmsSource.MODIS_SP: "modis/{year}/modis_{year}_{country}.csv",
    FirmsSource.VIIRS_SNPP_SP: "viirs-snpp/{year}/viirs-snpp_{year}_{country}.csv",
}

# FIRMS "type" column (archives only): 0 vegetation fire, 1 active volcano,
# 2 other static land source (gas flares, industry), 3 offshore.
STATIC_FIRE_TYPES = {1, 2, 3}


class ConfidenceLevel(StrEnum):
    LOW = "low"
    NOMINAL = "nominal"
    HIGH = "high"


CONFIDENCE_RANK = {ConfidenceLevel.LOW: 0, ConfidenceLevel.NOMINAL: 1, ConfidenceLevel.HIGH: 2}


def sensor_of(source: FirmsSource) -> Sensor:
    return Sensor.MODIS if source.startswith("MODIS") else Sensor.VIIRS
