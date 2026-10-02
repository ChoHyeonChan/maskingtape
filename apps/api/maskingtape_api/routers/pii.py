# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from maskingtape_api.errors import ERROR_RESPONSES, server_error
from maskingtape_api.rate_limit import InMemoryRateLimiter, _client_key, enforce_rate_limit
from maskingtape_api.schemas import (
    AnonymizeRequest,
    AnonymizeResponse,
    ProcessingMode,
    ScanRequest,
    ScanResponse,
)
from maskingtape_api.services.core_adapter import (
    CoreEngineAdapter,
    CoreEngineError,
    get_core_adapter,
)
from maskingtape_api.services.name_judge import NameJudge
from maskingtape_api.services.openai_name_judge import openai_name_judge_from_env
from maskingtape_api.settings import DEFAULT_HYBRID_MAX_TEXT_LENGTH

router = APIRouter(tags=["pii"])


@router.post(
    "/scan",
    response_model=ScanResponse,
    responses=ERROR_RESPONSES,
)
def scan(
    request: ScanRequest,
    http_request: Request = None,
    core: CoreEngineAdapter = Depends(get_core_adapter),
    name_judge: NameJudge | None = Depends(openai_name_judge_from_env),
    _rate_limit: None = Depends(enforce_rate_limit),
) -> ScanResponse | JSONResponse:
    """Detect personal information using rule or hybrid mode."""
    try:
        return core.scan(
            request.text,
            request.mode,
            _usable_name_judge(name_judge),
            _hybrid_preflight_failure(request, http_request),
        )
    except CoreEngineError:
        return server_error("core_scan_failed", "core 탐지 엔진 호출에 실패했습니다.")


@router.post(
    "/anonymize",
    response_model=AnonymizeResponse,
    responses=ERROR_RESPONSES,
)
def anonymize(
    request: AnonymizeRequest,
    http_request: Request = None,
    core: CoreEngineAdapter = Depends(get_core_adapter),
    name_judge: NameJudge | None = Depends(openai_name_judge_from_env),
    _rate_limit: None = Depends(enforce_rate_limit),
) -> AnonymizeResponse | JSONResponse:
    """Anonymize personal information using rule or hybrid mode."""
    try:
        return core.anonymize(
            request.text,
            request.strategy,
            request.mode,
            _usable_name_judge(name_judge),
            _hybrid_preflight_failure(request, http_request),
        )
    except CoreEngineError:
        return server_error(
            "core_anonymize_failed",
            "core 비식별화 엔진 호출에 실패했습니다.",
        )


def _usable_name_judge(name_judge: Any) -> NameJudge | None:
    """Direct unit calls receive FastAPI's Depends marker; treat that as no judge."""
    return cast(NameJudge, name_judge) if hasattr(name_judge, "find_names") else None


def _hybrid_preflight_failure(
    request: ScanRequest | AnonymizeRequest,
    http_request: Request | None,
) -> str | None:
    if request.mode != ProcessingMode.HYBRID:
        return None

    max_text_length = DEFAULT_HYBRID_MAX_TEXT_LENGTH
    if http_request is not None:
        max_text_length = getattr(
            http_request.app.state,
            "hybrid_max_text_length",
            DEFAULT_HYBRID_MAX_TEXT_LENGTH,
        )
    if len(request.text) > max_text_length:
        return "input_too_long"

    if http_request is None:
        return None

    limiter: InMemoryRateLimiter | None = getattr(
        http_request.app.state,
        "hybrid_rate_limiter",
        None,
    )
    if limiter is None:
        return None

    trusted_headers: tuple[str, ...] = getattr(
        http_request.app.state,
        "trusted_client_ip_headers",
        (),
    )
    result = limiter.check(_client_key(http_request, trusted_headers))
    return None if result.allowed else "rate_limited"
