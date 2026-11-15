from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models.weather_forecast_model import WeatherForecast


def get_forecast(session: Session, latitude: float, longitude: float) -> WeatherForecast | None:
    query = select(WeatherForecast).where(
        WeatherForecast.latitude == latitude, WeatherForecast.longitude == longitude
    )
    return session.scalars(query).first()


def save_forecast(
    session: Session,
    latitude: float,
    longitude: float,
    forecast: dict,
    air_quality: dict | None,
    fetched_at: datetime,
) -> None:
    values = {"forecast": forecast, "air_quality": air_quality, "fetched_at": fetched_at}
    query = (
        insert(WeatherForecast)
        .values(latitude=latitude, longitude=longitude, **values)
        .on_conflict_do_update(constraint="uq_weather_forecast_point", set_=values)
    )
    session.execute(query)
    session.commit()
