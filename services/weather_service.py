"""Open-Meteo forecast and dust for a point, stored in weather_forecasts and reused while fresh."""

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from configurations.environment_config import environment
from configurations.logger_config import logger
from repositories import weather_forecast_repository
from utilities.api_error_util import ApiError

# The same fields the Beacon website asks Open-Meteo for (src/lib/weather.ts).
DAILY_FIELDS = (
    "temperature_2m_max,relative_humidity_2m_min,wind_speed_10m_max,wind_gusts_10m_max,"
    "precipitation_sum,vapour_pressure_deficit_max,et0_fao_evapotranspiration"
)
CURRENT_FIELDS = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"


def fetch_open_meteo(latitude: float, longitude: float) -> tuple[dict, dict | None]:
    point = {"latitude": latitude, "longitude": longitude}
    with httpx.Client(timeout=30) as client:
        forecast = client.get(
            environment.OPEN_METEO_FORECAST_URL,
            params={
                **point,
                "daily": DAILY_FIELDS,
                "current": CURRENT_FIELDS,
                "past_days": 30,
                "forecast_days": 7,
                "timezone": "auto",
            },
        )
        if forecast.status_code != 200:
            raise ApiError(502, f"Open-Meteo forecast failed ({forecast.status_code})")
        try:
            air = client.get(
                environment.OPEN_METEO_AIR_QUALITY_URL,
                params={**point, "hourly": "dust", "forecast_days": 3},
            )
            air_quality = air.json() if air.status_code == 200 else None
        except httpx.HTTPError as error:
            logger.warning("Open-Meteo dust failed: %s", error)
            air_quality = None
    return forecast.json(), air_quality


def get_weather(session: Session, latitude: float, longitude: float) -> dict:
    latitude, longitude = round(latitude, 1), round(longitude, 1)
    cached = weather_forecast_repository.get_forecast(session, latitude, longitude)
    max_age = timedelta(minutes=environment.WEATHER_CACHE_MINUTES)
    if cached and datetime.now(UTC) - cached.fetched_at < max_age:
        forecast, air_quality, fetched_at = cached.forecast, cached.air_quality, cached.fetched_at
    else:
        session.rollback()  # return the connection to the pool while Open-Meteo answers
        forecast, air_quality = fetch_open_meteo(latitude, longitude)
        fetched_at = datetime.now(UTC)
        weather_forecast_repository.save_forecast(
            session, latitude, longitude, forecast, air_quality, fetched_at
        )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "fetched_at": fetched_at.isoformat(),
        "forecast": forecast,
        "air_quality": air_quality,
    }
