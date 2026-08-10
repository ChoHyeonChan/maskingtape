# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI
from fastapi.testclient import TestClient

from maskingtape_api.main import create_app
from maskingtape_api.settings import ApiSettings


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


def test_rate_limit_uses_forwarded_client_ip() -> None:
    client = TestClient(_rate_limited_app(limit=1))
    body = {"text": "합성 테스트 문장입니다"}

    assert client.post(
        "/scan",
        json=body,
        headers={"x-forwarded-for": "203.0.113.10"},
    ).status_code == 200
    assert client.post(
        "/scan",
        json=body,
        headers={"x-forwarded-for": "203.0.113.11"},
    ).status_code == 200


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
        )
    )
