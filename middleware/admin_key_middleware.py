import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from configurations.environment_config import environment
from utilities.api_error_util import ApiError

admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin_key(x_admin_key: str | None = Security(admin_key_header)) -> None:
    """Route dependency for ingestion endpoints. Open when ADMIN_API_KEY is not set (local use)."""
    expected = environment.ADMIN_API_KEY
    if expected and not secrets.compare_digest(x_admin_key or "", expected):
        raise ApiError(401, "Missing or wrong X-Admin-Key header")
