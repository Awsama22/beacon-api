from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from configurations.cors_config import cors_options


def add_cors_middleware(application: FastAPI) -> None:
    application.add_middleware(CORSMiddleware, **cors_options)
