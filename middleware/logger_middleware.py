import time

from fastapi import FastAPI, Request

from configurations.logger_config import logger


def add_logger_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def log_request(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response
