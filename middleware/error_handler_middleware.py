from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from configurations.logger_config import logger
from utilities.api_error_util import ApiError
from utilities.api_response_util import error_response


def add_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError):
        return JSONResponse(error_response(error.message), status_code=error.status_code)

    @application.exception_handler(HTTPException)
    async def handle_http_error(_: Request, error: HTTPException):
        message = "Route not found" if error.status_code == 404 else str(error.detail)
        return JSONResponse(error_response(message), status_code=error.status_code)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError):
        # Only location and message: the raw errors can hold exception objects JSON can't encode.
        details = [{"location": e["loc"], "message": e["msg"]} for e in error.errors()]
        return JSONResponse(error_response("Invalid request", details), status_code=422)

    @application.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception):
        logger.exception("Unhandled error", exc_info=error)
        return JSONResponse(error_response("Internal server error"), status_code=500)
