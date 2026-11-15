from collections import defaultdict

from sqlalchemy.orm import Session

from models.fire_detection_model import FireDetection
from repositories import fire_detection_repository
from validators.fire_validator import FireAreaQuery, FireNearQuery


def serialize(detection: FireDetection) -> dict:
    return {
        "id": detection.id,
        "source": detection.source,
        "sensor": detection.sensor,
        "satellite": detection.satellite,
        "latitude": detection.latitude,
        "longitude": detection.longitude,
        "acquired_at": detection.acquired_at.isoformat(),
        "brightness": detection.brightness,
        "frp": detection.frp,
        "confidence": detection.confidence,
        "confidence_level": detection.confidence_level,
        "day_night": detection.day_night,
        "fire_type": detection.fire_type,
        "is_static_source": detection.is_static_source,
    }


def find_in_area(session: Session, query: FireAreaQuery) -> dict:
    detections = fire_detection_repository.find_in_box(session, query)
    return {"count": len(detections), "fires": [serialize(d) for d in detections]}


def find_near(session: Session, query: FireNearQuery) -> dict:
    rows = fire_detection_repository.find_near(session, query)
    fires = [{**serialize(d), "distance_km": round(km, 2)} for d, km in rows]
    return {"count": len(fires), "fires": fires}


def monthly_counts(session: Session, query: FireAreaQuery) -> dict:
    """Hot spots per month and sensor in a box (the burning calendar), with each source's share."""
    months: dict[str, dict] = defaultdict(lambda: {"MODIS": 0, "VIIRS": 0, "sources": {}})
    for month, sensor, source, count in fire_detection_repository.monthly_counts(session, query):
        entry = months[month.strftime("%Y-%m")]
        entry[sensor] += count
        entry["sources"][source] = count
    return {"months": [{"month": key, **value} for key, value in months.items()]}
