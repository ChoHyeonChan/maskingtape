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
def anonymize(_: AnonymizeRequest) -> JSONResponse:
    """Declare the anonymize API contract. Core integration is implemented later."""
    return _not_implemented(
        "anonymize_not_implemented",
        "/anonymize 구현은 scan 및 core 연동 이후 연결합니다.",
    )


def _not_implemented(code: str, message: str) -> JSONResponse:
    return _error_response(status.HTTP_501_NOT_IMPLEMENTED, code, message)


def _server_error(code: str, message: str) -> JSONResponse:
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, code, message)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    error = ErrorResponse(code=code, message=message)
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(mode="json"),
    )
