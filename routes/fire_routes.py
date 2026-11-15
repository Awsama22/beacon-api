from fastapi import APIRouter

from controllers import fire_controller

fire_router = APIRouter(tags=["Fires"])
fire_router.add_api_route(
    "", fire_controller.list_fires, methods=["GET"], summary="Stored fire detections in a box"
)
fire_router.add_api_route(
    "/near",
    fire_controller.fires_near,
    methods=["GET"],
    summary="Stored fire detections within a radius of a point, nearest first",
)
fire_router.add_api_route(
    "/monthly-counts",
    fire_controller.monthly_counts,
    methods=["GET"],
    summary="Hot spots per month and sensor in a box (burning calendar)",
)
fire_router.add_api_route(
    "/live",
    fire_controller.live_fires,
    methods=["GET"],
    summary="Last 7 days of near-real-time fires in the website's live.json shape (cached)",
)
