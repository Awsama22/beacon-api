from services.health_service import get_health
from utilities.api_response_util import success_response


def health_check() -> dict:
    return success_response(get_health())
