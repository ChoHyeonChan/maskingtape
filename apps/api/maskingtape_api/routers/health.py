# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter

from maskingtape_api.schemas import HealthResponse
from maskingtape_api.services.openai_name_judge import openai_name_judge_from_env

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return liveness and whether the optional hybrid judge can be selected."""
    return HealthResponse(
        status="ok",
        hybrid_available=openai_name_judge_from_env() is not None,
    )
