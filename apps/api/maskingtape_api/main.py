# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI

from maskingtape_api.routers.health import router as health_router


def create_app() -> FastAPI:
    """Build the FastAPI application with all API routers attached."""
    app = FastAPI(
        title="maskingtape API",
        version="0.1.0",
        description="REST API wrapper for the maskingtape core engine.",
    )
    app.include_router(health_router)
    return app


app = create_app()
