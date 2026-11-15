"""Turns FIRMS CSV rows (near-real-time files, Area API, archives) into fire_detections rows."""

from datetime import UTC, datetime

from constants.firms_constants import STATIC_FIRE_TYPES, ConfidenceLevel, FirmsSource, sensor_of

VIIRS_CONFIDENCE = {
    "l": ConfidenceLevel.LOW,
    "low": ConfidenceLevel.LOW,
    "n": ConfidenceLevel.NOMINAL,
    "nominal": ConfidenceLevel.NOMINAL,
    "h": ConfidenceLevel.HIGH,
    "high": ConfidenceLevel.HIGH,
}


def confidence_level(raw: str) -> ConfidenceLevel | None:
    """MODIS 0-100 maps to low/nominal/high (<30, 30-79, 80+), like VIIRS l/n/h (FIRMS guidance)."""
    value = raw.strip().lower()
    if value in VIIRS_CONFIDENCE:
        return VIIRS_CONFIDENCE[value]
    try:
        number = float(value)
    except ValueError:
        return None
    if number < 30:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.NOMINAL if number < 80 else ConfidenceLevel.HIGH


def optional_float(raw: str | None) -> float | None:
    try:
        return float(raw) if raw not in (None, "") else None
    except ValueError:
        return None


def parse_detection(row: dict[str, str], source: FirmsSource) -> dict | None:
    """One CSV row to a fire_detections row, or None when the row is unusable."""
    try:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        acquired_at = datetime.strptime(
            f"{row['acq_date']} {row['acq_time'].strip().zfill(4)}", "%Y-%m-%d %H%M"
        ).replace(tzinfo=UTC)
    except (KeyError, ValueError):
        return None
    confidence = (row.get("confidence") or "").strip()
    level = confidence_level(confidence)
    if level is None:
        return None
    fire_type_raw = (row.get("type") or "").strip()
    fire_type = int(fire_type_raw) if fire_type_raw.isdigit() else None
    return {
        "source": source,
        "sensor": sensor_of(source),
        "satellite": (row.get("satellite") or "").strip()[:8],
        "latitude": latitude,
        "longitude": longitude,
        "acquired_at": acquired_at,
        "brightness": optional_float(row.get("brightness") or row.get("bright_ti4")),
        "frp": optional_float(row.get("frp")),
        "confidence": confidence[:8],
        "confidence_level": level,
        "day_night": (row.get("daynight") or "").strip()[:1] or None,
        "fire_type": fire_type,
        "is_static_source": None if fire_type is None else fire_type in STATIC_FIRE_TYPES,
    }
