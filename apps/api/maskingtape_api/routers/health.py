# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter

from maskingtape_api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a small liveness response for local and CI checks."""
    return HealthResponse(status="ok")
