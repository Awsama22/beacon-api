from typing import Annotated

from fastapi import Query

from configurations.database_config import DatabaseSession
from services import weather_service
from utilities.api_response_util import success_response


def get_weather(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    session: DatabaseSession,
) -> dict:
    return success_response(weather_service.get_weather(session, latitude, longitude))
