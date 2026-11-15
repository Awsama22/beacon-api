from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    PORT: int = 8040
    LOG_LEVEL: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5434
    POSTGRES_USER: str = "natoor"
    POSTGRES_DB: str = "natoor"
    POSTGRES_PASSWORD_FILE: str = "~/.config/natoor/postgres-password"
    # When set, ingestion endpoints need it in the X-Admin-Key header.
    ADMIN_API_KEY: str = ""
    # Free key from https://firms.modaps.eosdis.nasa.gov/api/map_key/, only for the FIRMS Area API.
    FIRMS_MAP_KEY: str = ""
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov"
    OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    WEATHER_CACHE_MINUTES: int = 60
    # Background fetch of FIRMS near-real-time fires; 0 turns it off.
    LIVE_REFRESH_MINUTES: int = 60
    NRT_RETENTION_DAYS: int = 30
    DOWNLOAD_TIMEOUT_SECONDS: int = 300


environment = Environment()
