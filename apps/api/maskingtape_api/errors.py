# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from maskingtape_api.schemas import MAX_TEXT_LENGTH, ErrorResponse

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid request"},
    413: {"model": ErrorResponse, "description": "Text payload too large"},
    429: {"model": ErrorResponse, "description": "Too many requests"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}


def server_error(code: str, message: str) -> JSONResponse:
    """내부 오류도 공개 API 계약의 에러 형식으로만 내보낸다.

    원래 예외 메시지는 원문 입력이나 의존 서비스 응답을 품을 수 있으므로, 라우터는
    고정 코드와 사람이 읽을 수 있는 안전한 문구만 넘긴다.
    """
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, code, message)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """모든 에러 응답을 `ErrorResponse` 스키마로 통일한다.

    FastAPI 기본 오류 모양을 그대로 쓰면 엔드포인트마다 필드가 달라지고, 프론트가
    실패 원인을 안정적으로 표시하기 어렵다. 헤더는 rate limit 같은 HTTP 의미를
    살려야 하는 경우에만 함께 붙인다.
    """
    error = ErrorResponse(code=code, message=message, details=details)
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(mode="json"),
        headers=headers,
    )


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """pydantic 검증 오류를 클라이언트에 안전한 요약으로 바꾼다.

    FastAPI의 원본 오류에는 사용자가 보낸 값이 섞일 수 있다. API 응답이 입력 원문을
    되비추지 않게, text 길이 초과는 413으로 승격하고 나머지는 타입·필드·허용된
    context만 남긴다.
    """
    errors = exc.errors()
    if _has_text_too_long_error(errors):
        return error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "text_too_large",
            f"text must be at most {MAX_TEXT_LENGTH} characters.",
            {"field": "text", "max_length": MAX_TEXT_LENGTH},
        )

    return error_response(
        status.HTTP_400_BAD_REQUEST,
        "invalid_request",
        "request body validation failed.",
        {"errors": [_sanitize_validation_error(error) for error in errors]},
    )


def _has_text_too_long_error(errors: list[dict[str, Any]]) -> bool:
    """문자 수 제한 위반만 별도로 찾아 413으로 응답하게 한다.

    바디 크기와 달리 pydantic의 문자열 길이 제한은 파싱 뒤에 걸리지만, 사용자에게는
    "요청 형식 오류"보다 "입력이 너무 큼"이 더 정확한 복구 힌트다.
    """
    return any(
        error.get("type") == "string_too_long"
        and tuple(error.get("loc", ())) == ("body", "text")
        for error in errors
    )


def _sanitize_validation_error(error: dict[str, Any]) -> dict[str, Any]:
    """검증 오류에서 원문 입력이 들어갈 수 있는 필드를 제거한다.

    오류 응답은 디버깅 힌트를 줘야 하지만 개인정보를 다시 노출하면 안 된다. 그래서
    타입, 위치, 화이트리스트된 context만 보존한다.
    """
    sanitized: dict[str, Any] = {
        "type": str(error.get("type", "validation_error")),
    }
    field = _field_name(error.get("loc", ()))
    if field:
        sanitized["field"] = field

    context = _safe_context(error.get("ctx"))
    if context:
        sanitized["context"] = context
    return sanitized


def _field_name(loc: Any) -> str | None:
    """FastAPI 내부 위치 표기에서 공개해도 되는 필드 경로만 만든다.

    `body`는 구현 세부라 클라이언트에게 도움이 적고, 나머지 경로만 남기면 폼/JSON
    필드 표시와 테스트 기대값이 단순해진다.
    """
    if not isinstance(loc, (list, tuple)):
        return None
    parts = [str(part) for part in loc if part != "body"]
    return ".".join(parts) if parts else None


def _safe_context(ctx: Any) -> dict[str, Any]:
    """검증 context 중 원문이 될 수 없는 값만 통과시킨다.

    pydantic context에는 제한값처럼 유용한 정보와 입력값처럼 민감할 수 있는 정보가 함께
    들어갈 수 있어, API 계약에 필요한 작은 집합만 허용한다.
    """
    if not isinstance(ctx, dict):
        return {}

    allowed: dict[str, Any] = {}
    for key in ("expected", "min_length", "max_length"):
        value = ctx.get(key)
        if isinstance(value, str | int | float | bool):
            allowed[key] = value
    return allowed
