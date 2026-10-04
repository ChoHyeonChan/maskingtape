# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

import http.client
import io
import urllib.error

import pytest
from fastapi.testclient import TestClient
from maskingtape.types import Detection
from maskingtape_api.main import create_app
from maskingtape_api.services.core_adapter import CoreEngineAdapter, get_core_adapter
from maskingtape_api.services.name_judge import NameJudgeError
from maskingtape_api.services.openai_name_judge import OpenAINameJudge, openai_name_judge_from_env
from maskingtape_api.settings import ApiSettings

_PHONE = "010-1234-5678"
_TEXT = f"담당자는 김민수이고 연락처 {_PHONE}입니다"


class PhoneOnlyPipeline:
    def scan(self, text: str) -> list[Detection]:
        start = text.find(_PHONE)
        if start == -1:
            return []
        return [
            Detection(
                kind="phone",
                start=start,
                end=start + len(_PHONE),
                text=_PHONE,
                confidence=1.0,
                detector="PhoneOnlyDetector",
            )
        ]


class FakeNameJudge:
    def __init__(self, names: list[str]) -> None:
        self.names = names
        self.calls: list[str] = []

    def find_names(self, masked_text: str) -> list[str]:
        self.calls.append(masked_text)
        return self.names


class FailingNameJudge:
    def __init__(self, code: str) -> None:
        self.code = code
        self.calls = 0

    def find_names(self, masked_text: str) -> list[str]:
        self.calls += 1
        raise NameJudgeError(self.code)


def test_rule_mode_does_not_call_name_judge() -> None:
    judge = FakeNameJudge(["김민수"])
    client = _client(judge)

    response = client.post("/scan", json={"text": _TEXT})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "rule"
    assert payload["hybrid_failed"] is False
    assert payload["hybrid_failure_code"] is None
    assert [d["kind"] for d in payload["detections"]] == ["phone"]
    assert judge.calls == []


def test_hybrid_scan_adds_name_from_fake_judge() -> None:
    judge = FakeNameJudge(["김민수"])
    client = _client(judge)

    response = client.post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "hybrid"
    assert payload["hybrid_failed"] is False
    assert payload["hybrid_failure_code"] is None
    assert [(d["kind"], d["detector"]) for d in payload["detections"]] == [
        ("name", "FakeNameJudge"),
        ("phone", "PhoneOnlyDetector"),
    ]
    assert judge.calls == ["담당자는 김민수이고 연락처 [전화번호]입니다"]


def test_hybrid_anonymize_uses_added_name_detection() -> None:
    client = _client(FakeNameJudge(["김민수"]))

    response = client.post("/anonymize", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "hybrid"
    assert "김민수" not in payload["text"]
    assert _PHONE not in payload["text"]
    assert [d["kind"] for d in payload["detections"]] == ["name", "phone"]


def test_hybrid_falls_back_to_rule_when_judge_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = _client(name_judge=None, override_name_judge=False)

    response = client.post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "rule"
    assert payload["hybrid_failed"] is True
    assert payload["hybrid_failure_code"] == "name_judge_unavailable"
    assert [d["kind"] for d in payload["detections"]] == ["phone"]


@pytest.mark.parametrize(
    "bad_key",
    [
        "test-key\nX-Injected: 1",
        "test-key한",
        "test-key\u200b",
    ],
    ids=["newline", "non-ascii", "zero-width-space"],
)
def test_hybrid_falls_back_to_rule_when_openai_key_is_invalid(monkeypatch, bad_key: str) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", bad_key)
    client = _client(name_judge=None, override_name_judge=False)

    response = client.post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    assert bad_key not in response.text
    payload = response.json()
    assert payload["mode_used"] == "rule"
    assert payload["hybrid_failed"] is True
    assert payload["hybrid_failure_code"] == "name_judge_unavailable"
    assert [d["kind"] for d in payload["detections"]] == ["phone"]


def test_hybrid_falls_back_to_rule_on_name_judge_error() -> None:
    judge = FailingNameJudge("refused")
    client = _client(judge)

    response = client.post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "rule"
    assert payload["hybrid_failed"] is True
    assert payload["hybrid_failure_code"] == "refused"
    assert [d["kind"] for d in payload["detections"]] == ["phone"]
    assert judge.calls == 1


def test_hybrid_timeout_code_is_returned_without_500() -> None:
    response = _client(FailingNameJudge("timeout")).post(
        "/scan",
        json={"text": _TEXT, "mode": "hybrid"},
    )

    assert response.status_code == 200
    assert response.json()["hybrid_failure_code"] == "timeout"


def test_hybrid_input_limit_falls_back_without_calling_judge() -> None:
    judge = FakeNameJudge(["김민수"])
    client = _client(
        judge,
        settings=ApiSettings(cors_allowed_origins=(), hybrid_max_text_length=5),
    )

    response = client.post("/scan", json={"text": "김민수입니다", "mode": "hybrid"})

    assert response.status_code == 200
    assert response.json()["mode_used"] == "rule"
    assert response.json()["hybrid_failure_code"] == "input_too_long"
    assert judge.calls == []


def test_hybrid_rate_limit_falls_back_to_rule() -> None:
    judge = FakeNameJudge(["김민수"])
    client = _client(
        judge,
        settings=ApiSettings(
            cors_allowed_origins=(),
            rate_limit_requests=100,
            hybrid_rate_limit_requests=1,
            hybrid_rate_limit_window_seconds=60,
        ),
    )

    first = client.post("/scan", json={"text": _TEXT, "mode": "hybrid"})
    second = client.post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert first.status_code == 200
    assert first.json()["mode_used"] == "hybrid"
    assert second.status_code == 200
    assert second.json()["mode_used"] == "rule"
    assert second.json()["hybrid_failure_code"] == "rate_limited"
    assert len(judge.calls) == 1


class RaisingOpener:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def open(self, request, timeout: float):
        raise self.error


@pytest.mark.parametrize(
    "error",
    [http.client.IncompleteRead(b"partial"), http.client.BadStatusLine("bad status")],
    ids=["incomplete-read", "bad-status-line"],
)
def test_hybrid_falls_back_when_openai_connection_breaks_mid_response(error) -> None:
    # 실제 판단기에 연결이 중간에 끊기는 오류를 넣어도 500이 아니라 규칙 결과로 돌아간다(#625).
    judge = OpenAINameJudge("test-key-not-a-real-openai-key", opener=RaisingOpener(error))

    response = _client(judge).post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "rule"
    assert payload["hybrid_failed"] is True
    assert payload["hybrid_failure_code"] == "network"
    assert [d["kind"] for d in payload["detections"]] == ["phone"]


def test_hybrid_falls_back_when_a_rate_limit_error_body_breaks() -> None:
    # 429 에러 본문을 읽다 연결이 끊겨도 500이 아니라 규칙 결과로 돌아간다(#625).
    class BrokenBody(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            raise http.client.IncompleteRead(b'{"error": ')

    error = urllib.error.HTTPError("https://api.openai.com/v1/responses", 429, "error", {}, BrokenBody())
    judge = OpenAINameJudge("test-key-not-a-real-openai-key", opener=RaisingOpener(error))

    response = _client(judge).post("/scan", json={"text": _TEXT, "mode": "hybrid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode_used"] == "rule"
    assert payload["hybrid_failure_code"] == "rate_limited"


def _client(
    name_judge,
    *,
    settings: ApiSettings | None = None,
    override_name_judge: bool = True,
) -> TestClient:
    app = create_app(
        settings=settings
        or ApiSettings(
            cors_allowed_origins=(),
            rate_limit_requests=100,
        )
    )
    app.dependency_overrides[get_core_adapter] = lambda: CoreEngineAdapter(
        pipeline=PhoneOnlyPipeline()
    )
    if override_name_judge:
        app.dependency_overrides[openai_name_judge_from_env] = lambda: name_judge
    return TestClient(app)
