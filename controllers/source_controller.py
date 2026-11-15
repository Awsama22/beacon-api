from configurations.database_config import DatabaseSession
from services import source_service
from utilities.api_response_util import success_response


def list_sources(session: DatabaseSession) -> dict:
    return success_response(source_service.list_sources(session))
