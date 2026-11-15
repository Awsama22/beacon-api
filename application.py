from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from configurations.environment_config import environment
from configurations.logger_config import logger
from middleware.cors_middleware import add_cors_middleware
from middleware.error_handler_middleware import add_error_handlers
from middleware.logger_middleware import add_logger_middleware
from routes.dataset_routes import archive_router, history_router, model_router
from routes.fire_routes import fire_router
from routes.health_routes import health_router
from routes.ingestion_routes import ingestion_router
from routes.source_routes import source_router
from routes.weather_routes import weather_router
from services import refresh_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = refresh_service.start()
    yield
    stop.set()


application = FastAPI(
    title="Beacon API",
    description="Fetches NASA FIRMS fire detections and Open-Meteo weather, stores them in "
    "PostgreSQL and serves them to the Beacon website and mobile app.",
    docs_url="/api-docs",
    redoc_url=None,
    lifespan=lifespan,
)

add_logger_middleware(application)
add_cors_middleware(application)
application.add_middleware(GZipMiddleware, minimum_size=1000)
add_error_handlers(application)
application.include_router(health_router, prefix="/health")
application.include_router(source_router, prefix="/sources")
application.include_router(ingestion_router, prefix="/ingestions")
application.include_router(fire_router, prefix="/fires")
application.include_router(weather_router, prefix="/weather")
application.include_router(archive_router, prefix="/archive")
application.include_router(history_router, prefix="/history")
application.include_router(model_router, prefix="/model")
application.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    import uvicorn

    logger.info("Beacon API started on port %s", environment.PORT)
    uvicorn.run("application:application", host="0.0.0.0", port=environment.PORT, reload=True)
