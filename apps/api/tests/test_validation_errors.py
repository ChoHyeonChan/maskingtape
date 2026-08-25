# SPDX-License-Identifier: Apache-2.0

import asyncio
import json

from fastapi.testclient import TestClient

from maskingtape_api.main import create_app
from maskingtape_api.schemas import MAX_TEXT_LENGTH
from maskingtape_api.settings import ApiSettings


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


def test_content_length_limit_rejects_body_before_schema_validation() -> None:
    response = TestClient(
        create_app(settings=ApiSettings(cors_allowed_origins=(), max_body_bytes=10))
    ).post(
        "/scan",
        content=b'{"text":"ok"}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "code": "request_body_too_large",
        "message": "request body must be at most 10 bytes.",
        "details": {"max_bytes": 10},
    }


def test_chunked_body_without_content_length_is_still_limited() -> None:
    # 보안: Content-Length 헤더만 검사하면 chunked 전송으로 상한을 우회할 수 있고,
    # 그러면 서버가 바디 전체를 메모리에 올린 뒤에야 걸린다. 실제 수신 바이트로 막는다.
    app = create_app(settings=ApiSettings(cors_allowed_origins=(), max_body_bytes=200))
    oversized = json.dumps({"text": "A" * 30_000}).encode()

    status_code, payload = _post_chunked(app, "/scan", oversized)

    assert status_code == 413
    assert payload["code"] == "request_body_too_large"
    assert payload["details"] == {"max_bytes": 200}


def test_chunked_body_within_limit_is_accepted() -> None:
    # 음성 대조 — 상한 안이면 chunked도 정상 처리된다(무조건 413이 아니다).
    app = create_app(settings=ApiSettings(cors_allowed_origins=(), max_body_bytes=10_000))
    body = json.dumps({"text": "합성 테스트 문장입니다"}).encode()

    status_code, _ = _post_chunked(app, "/scan", body)

    assert status_code == 200


def _post_chunked(app, path: str, body: bytes, chunk_size: int = 4096):
    """Content-Length 없이 바디를 여러 조각으로 흘려보낸다(= chunked 전송).

    TestClient는 항상 Content-Length를 붙여서 이 경로를 재현할 수 없어 ASGI로 직접 호출한다.
    """
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    chunks = [body[i : i + chunk_size] for i in range(0, len(body), chunk_size)] or [b""]
    pending = list(chunks)
    received: dict[str, object] = {}

    async def receive():
        if pending:
            chunk = pending.pop(0)
            return {"type": "http.request", "body": chunk, "more_body": bool(pending)}
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            received["status"] = message["status"]
        elif message["type"] == "http.response.body":
            received["body"] = received.get("body", b"") + message.get("body", b"")

    asyncio.run(app(scope, receive, send))
    raw = received.get("body", b"")
    payload = json.loads(raw) if raw else {}
    return received.get("status"), payload


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
