# SPDX-License-Identifier: Apache-2.0

from fastapi.testclient import TestClient

from maskingtape_api.main import create_app
from maskingtape_api.schemas import MAX_TEXT_LENGTH


def test_empty_text_validation_uses_shared_error_shape() -> None:
    response = TestClient(create_app()).post("/scan", json={"text": ""})

    assert response.status_code == 400
    assert response.json() == {
        "code": "invalid_request",
        "message": "request body validation failed.",
        "details": {
            "errors": [
                {
                    "type": "string_too_short",
                    "field": "text",
                    "context": {"min_length": 1},
                }
            ]
        },
    }


def test_too_long_text_validation_returns_413_without_echoing_input() -> None:
    long_text = "x" * (MAX_TEXT_LENGTH + 1)

    response = TestClient(create_app()).post("/scan", json={"text": long_text})

    assert response.status_code == 413
    assert response.json() == {
        "code": "text_too_large",
        "message": f"text must be at most {MAX_TEXT_LENGTH} characters.",
        "details": {"field": "text", "max_length": MAX_TEXT_LENGTH},
    }
    assert long_text not in response.text


def test_invalid_strategy_validation_does_not_echo_text() -> None:
    text = "Contact sample@example.com"

    response = TestClient(create_app()).post(
        "/anonymize",
        json={"text": text, "strategy": "drop"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "invalid_request"
    assert payload["details"]["errors"][0]["field"] == "strategy"
    assert payload["details"]["errors"][0]["type"] == "enum"
    assert text not in response.text
