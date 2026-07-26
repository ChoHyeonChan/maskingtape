# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from maskingtape_api.schemas import (
    AnonymizeRequest,
    AnonymizeResponse,
    ErrorResponse,
    ScanRequest,
    ScanResponse,
)

router = APIRouter(tags=["pii"])

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "잘못된 요청"},
    413: {"model": ErrorResponse, "description": "입력 크기 초과"},
    500: {"model": ErrorResponse, "description": "서버 내부 오류"},
}


@router.post(
    "/scan",
    response_model=ScanResponse,
    responses={**ERROR_RESPONSES, 501: {"model": ErrorResponse, "description": "미구현"}},
)
def scan(_: ScanRequest) -> JSONResponse:
    """Declare the scan API contract. Core integration is implemented in the next issue."""
    return _not_implemented("scan_not_implemented", "/scan 구현은 다음 작업에서 core와 연결합니다.")


@router.post(
    "/anonymize",
    response_model=AnonymizeResponse,
    responses={**ERROR_RESPONSES, 501: {"model": ErrorResponse, "description": "미구현"}},
)
def anonymize(_: AnonymizeRequest) -> JSONResponse:
    """Declare the anonymize API contract. Core integration is implemented later."""
    return _not_implemented(
        "anonymize_not_implemented",
        "/anonymize 구현은 scan 및 core 연동 이후 연결합니다.",
    )


def _not_implemented(code: str, message: str) -> JSONResponse:
    error = ErrorResponse(code=code, message=message)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content=error.model_dump(mode="json"),
    )
