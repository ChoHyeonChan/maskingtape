# SPDX-License-Identifier: Apache-2.0

from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi

from maskingtape_api.errors import validation_exception_handler
from maskingtape_api.routers.health import router as health_router
from maskingtape_api.routers.pii import router as pii_router


def create_app() -> FastAPI:
    """Build the FastAPI application with all API routers attached."""
    app = FastAPI(
        title="maskingtape API",
        version="0.1.0",
        description="REST API wrapper for the maskingtape core engine.",
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(health_router)
    app.include_router(pii_router)
    app.openapi = lambda: _openapi_without_default_422(app)
    return app


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
