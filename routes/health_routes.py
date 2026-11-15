from fastapi import APIRouter

from controllers.health_controller import health_check

health_router = APIRouter(tags=["Health"])
health_router.add_api_route("", health_check, methods=["GET"], summary="Health check")
