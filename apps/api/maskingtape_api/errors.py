# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from maskingtape_api.schemas import MAX_TEXT_LENGTH, ErrorResponse

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid request"},
    404: {"model": ErrorResponse, "description": "Route not found"},
    405: {"model": ErrorResponse, "description": "Method not allowed"},
    413: {"model": ErrorResponse, "description": "Text payload too large"},
    429: {"model": ErrorResponse, "description": "Too many requests"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}


def server_error(code: str, message: str) -> JSONResponse:
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, code, message)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
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


async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return error_response(status.HTTP_404_NOT_FOUND, "not_found", "route not found.")
    if exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return error_response(
            status.HTTP_405_METHOD_NOT_ALLOWED,
            "method_not_allowed",
            "method not allowed.",
            headers=exc.headers,
        )
    return error_response(exc.status_code, "http_error", "request failed.")


def _has_text_too_long_error(errors: list[dict[str, Any]]) -> bool:
    return any(
        error.get("type") == "string_too_long"
        and tuple(error.get("loc", ())) == ("body", "text")
        for error in errors
    )


def _sanitize_validation_error(error: dict[str, Any]) -> dict[str, Any]:
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
    if not isinstance(loc, (list, tuple)):
        return None
    parts = [str(part) for part in loc if part != "body"]
    return ".".join(parts) if parts else None


def _safe_context(ctx: Any) -> dict[str, Any]:
    if not isinstance(ctx, dict):
        return {}

    allowed: dict[str, Any] = {}
    for key in ("expected", "min_length", "max_length"):
        value = ctx.get(key)
        if isinstance(value, str | int | float | bool):
            allowed[key] = value
    return allowed
