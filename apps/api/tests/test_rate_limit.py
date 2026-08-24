# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI
from fastapi.testclient import TestClient

from maskingtape_api.main import create_app
from maskingtape_api.rate_limit import InMemoryRateLimiter
from maskingtape_api.settings import ApiSettings


class Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_scan_returns_429_after_rate_limit_is_exceeded() -> None:
    client = TestClient(_rate_limited_app(limit=2))
    body = {"text": "합성 테스트 문장입니다"}

    assert client.post("/scan", json=body).status_code == 200
    assert client.post("/scan", json=body).status_code == 200

    response = client.post("/scan", json=body)

    assert response.status_code == 429
    assert response.json() == {
        "code": "rate_limit_exceeded",
        "message": "too many requests.",
        "details": {"limit": 2, "window_seconds": 60},
    }
    assert 1 <= int(response.headers["retry-after"]) <= 60


def test_anonymize_returns_429_after_rate_limit_is_exceeded() -> None:
    client = TestClient(_rate_limited_app(limit=1))
    body = {"text": "합성 테스트 문장입니다"}

    assert client.post("/anonymize", json=body).status_code == 200

    response = client.post("/anonymize", json=body)

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limit_exceeded"


def test_rate_limit_ignores_spoofable_x_forwarded_for() -> None:
    client = TestClient(_rate_limited_app(limit=1))
    body = {"text": "합성 테스트 문장입니다"}

    assert client.post(
        "/scan",
        json=body,
        headers={"x-forwarded-for": "203.0.113.10"},
    ).status_code == 200
    response = client.post(
        "/scan",
        json=body,
        headers={"x-forwarded-for": "203.0.113.11"},
    )

    assert response.status_code == 429


def test_rate_limit_uses_trusted_platform_client_ip_headers() -> None:
    client = TestClient(_rate_limited_app(limit=1))
    body = {"text": "합성 테스트 문장입니다"}

    assert client.post(
        "/scan",
        json=body,
        headers={"x-vercel-forwarded-for": "203.0.113.10"},
    ).status_code == 200
    assert client.post(
        "/scan",
        json=body,
        headers={"x-vercel-forwarded-for": "203.0.113.11"},
    ).status_code == 200


def test_rate_limiter_caps_bucket_count_with_lru_eviction() -> None:
    clock = Clock()
    limiter = InMemoryRateLimiter(
        limit=1,
        window_seconds=60,
        max_buckets=3,
        now=clock,
    )

    for index in range(10):
        assert limiter.check(f"client-{index}").allowed

    assert limiter.bucket_count == 3


def test_rate_limiter_prunes_expired_empty_buckets() -> None:
    clock = Clock()
    limiter = InMemoryRateLimiter(
        limit=1,
        window_seconds=60,
        max_buckets=10,
        now=clock,
    )

    assert limiter.check("client-a").allowed
    assert limiter.check("client-b").allowed

    clock.value = 61
    assert limiter.check("client-c").allowed

    assert limiter.bucket_count == 1


def test_rate_limit_does_not_apply_to_health_endpoint() -> None:
    client = TestClient(_rate_limited_app(limit=1))

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200


def _rate_limited_app(limit: int) -> FastAPI:
    return create_app(
        settings=ApiSettings(
            cors_allowed_origins=(),
            rate_limit_requests=limit,
            rate_limit_window_seconds=60,
            rate_limit_max_buckets=10,
        )
    )
