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


def test_rate_limit_ignores_client_ip_headers_when_not_configured_as_trusted() -> None:
    # 기본값(신뢰 헤더 없음)에서는 x-vercel-forwarded-for·x-real-ip도 믿지 않는다 —
    # 프록시가 덮어써 준다는 보장이 없는 배포(맨 uvicorn 등)에서 이 헤더를 신뢰하면
    # 값만 바꿔가며 요청해 rate limit을 통째로 우회할 수 있다.
    for header in ("x-vercel-forwarded-for", "x-real-ip"):
        client = TestClient(_rate_limited_app(limit=1))
        body = {"text": "합성 테스트 문장입니다"}

        assert client.post(
            "/scan",
            json=body,
            headers={header: "203.0.113.10"},
        ).status_code == 200
        assert client.post(
            "/scan",
            json=body,
            headers={header: "203.0.113.11"},
        ).status_code == 429


def test_rate_limit_uses_client_ip_header_when_configured_as_trusted() -> None:
    # 신뢰 프록시 뒤(Vercel 등)라고 명시하면 그 헤더로 클라이언트를 구분한다 —
    # 그래야 한 사용자의 과다 요청이 다른 사용자를 막지 않는다.
    client = TestClient(
        _rate_limited_app(limit=1, trusted_client_ip_headers=("x-vercel-forwarded-for",))
    )
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
    # 같은 IP를 다시 쓰면 그 IP의 한도는 그대로 적용된다
    assert client.post(
        "/scan",
        json=body,
        headers={"x-vercel-forwarded-for": "203.0.113.10"},
    ).status_code == 429


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


def _rate_limited_app(
    limit: int,
    trusted_client_ip_headers: tuple[str, ...] = (),
) -> FastAPI:
    return create_app(
        settings=ApiSettings(
            cors_allowed_origins=(),
            rate_limit_requests=limit,
            rate_limit_window_seconds=60,
            rate_limit_max_buckets=10,
            trusted_client_ip_headers=trusted_client_ip_headers,
        )
    )
