from typing import Annotated

from fastapi import Query, Request, Response

from configurations.database_config import DatabaseSession
from services import fire_service, live_fire_service
from utilities.api_response_util import success_response
from utilities.cached_body_util import body_response
from validators.fire_validator import FireAreaQuery, FireNearQuery


def list_fires(query: Annotated[FireAreaQuery, Query()], session: DatabaseSession) -> dict:
    return success_response(fire_service.find_in_area(session, query))


def fires_near(query: Annotated[FireNearQuery, Query()], session: DatabaseSession) -> dict:
    return success_response(fire_service.find_near(session, query))


def monthly_counts(query: Annotated[FireAreaQuery, Query()], session: DatabaseSession) -> dict:
    return success_response(fire_service.monthly_counts(session, query))


def live_fires(request: Request, session: DatabaseSession) -> Response:
    return body_response(request, live_fire_service.get_live_body(session))
