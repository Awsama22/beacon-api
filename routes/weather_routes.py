from fastapi import APIRouter

from controllers.weather_controller import get_weather

weather_router = APIRouter(tags=["Weather"])
weather_router.add_api_route(
    "", get_weather, methods=["GET"], summary="Open-Meteo forecast and dust for a point (cached)"
)
