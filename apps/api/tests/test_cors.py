# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from maskingtape_api.main import create_app
from maskingtape_api.settings import ApiSettings


def test_cors_allows_configured_local_web_origin() -> None:
    origin = "http://localhost:5173"
    response = TestClient(create_app()).options(
        "/scan",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_rejects_unconfigured_origin() -> None:
    response = TestClient(create_app()).options(
        "/scan",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_can_use_explicit_origin_settings() -> None:
    origin = "https://demo.example"
    app = create_app(settings=ApiSettings(cors_allowed_origins=(origin,)))

    response = TestClient(app).options(
        "/anonymize",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
