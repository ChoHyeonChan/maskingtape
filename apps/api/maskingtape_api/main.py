# SPDX-License-Identifier: Apache-2.0

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from maskingtape_api.errors import error_response, validation_exception_handler
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
        max_buckets=settings.rate_limit_max_buckets,
    )
    _configure_body_size_limit(app, settings)
    _configure_cors(app, settings)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.include_router(health_router)
    app.include_router(pii_router)
    app.openapi = lambda: _openapi_without_default_422(app)
    return app


def _configure_body_size_limit(app: FastAPI, settings: ApiSettings) -> None:
    @app.middleware("http")
    async def reject_large_request_body(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = _content_length(request)
        if content_length is not None and content_length > settings.max_body_bytes:
            return error_response(
                status.HTTP_413_CONTENT_TOO_LARGE,
                "request_body_too_large",
                f"request body must be at most {settings.max_body_bytes} bytes.",
                {"max_bytes": settings.max_body_bytes},
            )
        return await call_next(request)


def _content_length(request: Request) -> int | None:
    raw_value = request.headers.get("content-length")
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value >= 0 else None


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
