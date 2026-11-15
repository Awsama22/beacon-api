from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class WeatherForecast(BaseModel):
    """Latest Open-Meteo forecast and dust for a point (rounded to 0.1°), reused until stale."""

    __tablename__ = "weather_forecasts"
    __table_args__ = (UniqueConstraint("latitude", "longitude", name="uq_weather_forecast_point"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    forecast: Mapped[dict] = mapped_column(JSONB)
    air_quality: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
