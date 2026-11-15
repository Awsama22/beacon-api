from fastapi import APIRouter

from controllers.source_controller import list_sources

source_router = APIRouter(tags=["Sources"])
source_router.add_api_route(
    "", list_sources, methods=["GET"], summary="FIRMS sources and their last successful fetch"
)
