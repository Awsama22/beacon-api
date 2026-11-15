import logging

from configurations.environment_config import environment

logging.basicConfig(
    level=environment.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# httpx logs every request URL at INFO; the FIRMS Area API URL holds FIRMS_MAP_KEY.
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("natoor-api")
