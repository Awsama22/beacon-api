from typing import Annotated

from fastapi import Path, Request, Response

from configurations.database_config import DatabaseSession
from constants.dataset_constants import DatasetName
from services import dataset_service
from utilities.cached_body_util import body_response


def dataset_route(name: DatasetName):
    def get_dataset(request: Request, session: DatabaseSession) -> Response:
        return body_response(request, dataset_service.dataset_body(session, name))

    return get_dataset


def history(request: Request, session: DatabaseSession) -> Response:
    return body_response(request, dataset_service.history_body(session))


def archive_grid(request: Request, session: DatabaseSession) -> Response:
    return body_response(request, dataset_service.grid_body(session))


def archive_tile(
    request: Request,
    tile_row: Annotated[int, Path(ge=0, lt=18)],
    tile_col: Annotated[int, Path(ge=0, lt=36)],
    session: DatabaseSession,
) -> Response:
    return body_response(request, dataset_service.tile_body(session, tile_row, tile_col))
