# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from maskingtape_api.main import create_app
from maskingtape_api.routers.health import health


def test_health_returns_ok_and_hybrid_unavailable_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert health().model_dump() == {"status": "ok", "hybrid_available": False}


def test_health_reports_hybrid_available_when_key_can_create_judge(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    assert health().model_dump() == {"status": "ok", "hybrid_available": True}


def test_health_reports_hybrid_unavailable_for_invalid_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test\nX-Injected: 1")

    assert health().model_dump() == {"status": "ok", "hybrid_available": False}


def test_health_route_is_registered() -> None:
    app = create_app()
    schema = app.openapi()

    assert "/health" in schema["paths"]
    assert "hybrid_available" in schema["components"]["schemas"]["HealthResponse"]["properties"]
