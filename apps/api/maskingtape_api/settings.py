# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
import os

DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_RATE_LIMIT_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class ApiSettings:
    """Runtime settings read from environment variables."""

    environment: str = "development"
    cors_allowed_origins: tuple[str, ...] = DEFAULT_CORS_ALLOWED_ORIGINS
    rate_limit_requests: int = DEFAULT_RATE_LIMIT_REQUESTS
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS


def get_api_settings() -> ApiSettings:
    return ApiSettings(
        environment=_env_value("MASKINGTAPE_API_ENV", "development"),
        cors_allowed_origins=_env_tuple(
            "MASKINGTAPE_API_CORS_ORIGINS",
            DEFAULT_CORS_ALLOWED_ORIGINS,
        ),
        rate_limit_requests=_env_int(
            "MASKINGTAPE_API_RATE_LIMIT_REQUESTS",
            DEFAULT_RATE_LIMIT_REQUESTS,
        ),
        rate_limit_window_seconds=_env_int(
            "MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS",
            DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        ),
    )


def _env_value(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_tuple(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    return tuple(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    return parsed if parsed > 0 else default
