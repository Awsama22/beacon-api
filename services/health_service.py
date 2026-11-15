from sqlalchemy import text

from configurations.database_config import get_database_engine
from configurations.logger_config import logger
from utilities.date_util import utc_now_iso


def get_database_status() -> str:
    try:
        with get_database_engine().connect() as connection:
            connection.execute(text("select 1"))
        return "ok"
    except Exception as error:
        logger.warning("Database check failed: %s", error)
        return "unavailable"


def get_health() -> dict:
    database = get_database_status()
    return {
        "status": "ok" if database == "ok" else "degraded",
        "service": "natoor-api",
        "database": database,
        "timestamp": utc_now_iso(),
    }
