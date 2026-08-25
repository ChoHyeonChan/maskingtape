# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
import os

DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_PRODUCTION_CORS_ALLOWED_ORIGINS: tuple[str, ...] = ()
DEFAULT_RATE_LIMIT_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_RATE_LIMIT_MAX_BUCKETS = 10_000
DEFAULT_MAX_BODY_BYTES = 1_000_000

# 신뢰 프록시 뒤에서만 의미가 있는 헤더들. 클라이언트가 직접 보낼 수 있는 값이라,
# 앞단 프록시가 반드시 덮어써 준다고 확신할 수 있을 때만 rate limit 키로 쓴다.
PROXY_CLIENT_IP_HEADERS = ("x-vercel-forwarded-for", "x-real-ip")


@dataclass(frozen=True)
class ApiSettings:
    """Runtime settings read from environment variables."""

    environment: str = "development"
    cors_allowed_origins: tuple[str, ...] = DEFAULT_CORS_ALLOWED_ORIGINS
    rate_limit_requests: int = DEFAULT_RATE_LIMIT_REQUESTS
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    rate_limit_max_buckets: int = DEFAULT_RATE_LIMIT_MAX_BUCKETS
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    # rate limit 키로 신뢰할 클라이언트 IP 헤더. 기본은 비어 있다(= TCP 소켓 주소만 사용).
    trusted_client_ip_headers: tuple[str, ...] = ()


def get_api_settings() -> ApiSettings:
    environment = _env_value("MASKINGTAPE_API_ENV", "development")
    default_cors_origins = (
        DEFAULT_PRODUCTION_CORS_ALLOWED_ORIGINS
        if environment == "production"
        else DEFAULT_CORS_ALLOWED_ORIGINS
    )
    return ApiSettings(
        environment=environment,
        cors_allowed_origins=_env_tuple(
            "MASKINGTAPE_API_CORS_ORIGINS",
            default_cors_origins,
        ),
        rate_limit_requests=_env_int(
            "MASKINGTAPE_API_RATE_LIMIT_REQUESTS",
            DEFAULT_RATE_LIMIT_REQUESTS,
        ),
        rate_limit_window_seconds=_env_int(
            "MASKINGTAPE_API_RATE_LIMIT_WINDOW_SECONDS",
            DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        ),
        rate_limit_max_buckets=_env_int(
            "MASKINGTAPE_API_RATE_LIMIT_MAX_BUCKETS",
            DEFAULT_RATE_LIMIT_MAX_BUCKETS,
        ),
        max_body_bytes=_env_int(
            "MASKINGTAPE_API_MAX_BODY_BYTES",
            DEFAULT_MAX_BODY_BYTES,
        ),
        trusted_client_ip_headers=_env_tuple(
            "MASKINGTAPE_API_TRUSTED_CLIENT_IP_HEADERS",
            _default_trusted_client_ip_headers(),
        ),
    )


def _default_trusted_client_ip_headers() -> tuple[str, ...]:
    """rate limit 키로 쓸 IP 헤더의 기본값 — 스푸핑이 불가능한 환경에서만 켠다.

    보안: 이 헤더들은 클라이언트가 임의로 붙일 수 있어서, 앞단이 덮어써 주지 않으면
    공격자가 값을 바꿔가며 요청할 때마다 새 버킷이 생겨 rate limit이 통째로 무력화된다.
    Vercel은 외부에서 들어온 forwarding 헤더를 플랫폼이 덮어써(IP 스푸핑 방지) 신뢰할 수
    있으므로, Vercel 런타임(`VERCEL` 환경변수)에서만 기본으로 켠다.

    그 외(맨 uvicorn 자체 호스팅 등)에서는 비워 두고 TCP 소켓 주소만 쓴다 — 프록시가
    이 헤더를 확실히 덮어쓰는 배포라면 `MASKINGTAPE_API_TRUSTED_CLIENT_IP_HEADERS`로
    명시해 켠다.
    """
    return PROXY_CLIENT_IP_HEADERS if os.getenv("VERCEL") else ()


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
