# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from maskingtape_api.errors import ERROR_RESPONSES, server_error
from maskingtape_api.schemas import (
    AnonymizeRequest,
    AnonymizeResponse,
    ScanRequest,
    ScanResponse,
)
from maskingtape_api.services.core_adapter import (
    CoreEngineAdapter,
    CoreEngineError,
    get_core_adapter,
)

router = APIRouter(tags=["pii"])


@router.post(
    "/scan",
    response_model=ScanResponse,
    responses=ERROR_RESPONSES,
)
def scan(
    request: ScanRequest,
    core: CoreEngineAdapter = Depends(get_core_adapter),
) -> ScanResponse | JSONResponse:
    """Detect personal information using the rule-based core pipeline."""
    try:
        return core.scan(request.text)
    except CoreEngineError:
        return server_error("core_scan_failed", "core 탐지 엔진 호출에 실패했습니다.")


@router.post(
    "/anonymize",
    response_model=AnonymizeResponse,
    responses=ERROR_RESPONSES,
)
def anonymize(
    request: AnonymizeRequest,
    core: CoreEngineAdapter = Depends(get_core_adapter),
) -> AnonymizeResponse | JSONResponse:
    """Anonymize personal information using the rule-based core pipeline."""
    try:
        return core.anonymize(request.text, request.strategy)
    except CoreEngineError:
        return server_error(
            "core_anonymize_failed",
            "core 비식별화 엔진 호출에 실패했습니다.",
        )
