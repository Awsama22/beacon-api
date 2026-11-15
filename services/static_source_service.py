from sqlalchemy.orm import Session

from repositories import static_source_repository
from utilities.static_source_util import grid_key


def replace_static_sources(session: Session, points: list[tuple[float, float]]) -> dict:
    """Replace the static source map and re-mark stored detections that have no FIRMS type."""
    keys = {(grid_key(latitude), grid_key(longitude)) for latitude, longitude in points}
    stored = static_source_repository.replace_all(session, keys)
    marked = static_source_repository.mark_detections(session)
    return {"static_sources": stored, "detections_changed": marked}
