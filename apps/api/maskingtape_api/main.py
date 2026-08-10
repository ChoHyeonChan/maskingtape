# SPDX-License-Identifier: Apache-2.0

from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from maskingtape_api.errors import validation_exception_handler
from maskingtape_api.rate_limit import (
    InMemoryRateLimiter,
    RateLimitExceeded,
    rate_limit_exception_handler,
)
from maskingtape_api.routers.health import router as health_router
from maskingtape_api.routers.pii import router as pii_router
from maskingtape_api.settings import ApiSettings, get_api_settings


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Build the FastAPI application with all API routers attached."""
    settings = settings if settings is not None else get_api_settings()
    app = FastAPI(
        title="maskingtape API",
        version="0.1.0",
        description="REST API wrapper for the maskingtape core engine.",
    )
    app.state.rate_limiter = InMemoryRateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    _configure_cors(app, settings)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.include_router(health_router)
    app.include_router(pii_router)
    app.openapi = lambda: _openapi_without_default_422(app)
    return app


def _configure_cors(app: FastAPI, settings: ApiSettings) -> None:
    if not settings.cors_allowed_origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type"],
    )


def _openapi_without_default_422(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation.get("responses", {}).pop("422", None)
    app.openapi_schema = schema
    return app.openapi_schema


app = create_app()
