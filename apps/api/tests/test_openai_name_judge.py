# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

import http.client
import io
import json
import urllib.error
import urllib.request

import pytest
from maskingtape_api.services.name_judge import NameJudgeError
from maskingtape_api.services.openai_name_judge import (
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_INPUT_CHARS,
    OPENAI_RESPONSES_URL,
    OpenAINameJudge,
    _NoRedirect,
    openai_name_judge_from_env,
)

# 규칙이 박서준·전화번호는 가렸고 이도현은 놓친 글(합성). 판단기는 이런 글만 받는다.
MASKED = "담당자 [이름] 과장([전화번호])이 이도현이랑 다음 주 회의 잡아 달래요."
KEY = "test-key-not-a-real-openai-key"


def _response(names=None, *, status="completed", extra_items=(), content=None) -> dict:
    if content is None:
        text = json.dumps({"names": names or []}, ensure_ascii=False)
        content = [{"type": "output_text", "text": text, "annotations": []}]
    message = {"type": "message", "role": "assistant", "status": "completed", "content": content}
    return {
        "object": "response",
        "status": status,
        "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
        "output": [*extra_items, message],
    }


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = io.BytesIO(body)

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakeOpener:
    def __init__(self, body: bytes = b"", error: Exception | None = None) -> None:
        self.body = body
        self.error = error
        self.requests: list[tuple[urllib.request.Request, float]] = []

    def open(self, request: urllib.request.Request, timeout: float) -> _FakeResponse:
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return _FakeResponse(self.body)


def _judge(payload=None, *, raw: bytes | None = None, error: Exception | None = None):
    body = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    opener = FakeOpener(body=body, error=error)
    return OpenAINameJudge(KEY, opener=opener), opener


def _http_error(status: int, body: dict | None = None) -> urllib.error.HTTPError:
    fp = io.BytesIO(json.dumps(body or {}).encode("utf-8"))
    return urllib.error.HTTPError(OPENAI_RESPONSES_URL, status, "error", {}, fp)


class _BrokenBody(io.BytesIO):
    """에러 본문을 읽는 도중 연결이 끊긴다(#625 후속)."""

    def read(self, size: int = -1) -> bytes:
        raise http.client.IncompleteRead(b'{"error": {"code": "rate_')


def _http_error_with_broken_body(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(OPENAI_RESPONSES_URL, status, "error", {}, _BrokenBody())


def _assert_no_attached_details(error: NameJudgeError) -> None:
    # `raise ... from None`이 빠지면 원래 예외(응답 본문이 딸린 HTTPError 등)가 추적에 따라 붙는다.
    assert error.__cause__ is None
    assert error.__context__ is None or error.__suppress_context__


def _assert_key_not_in_exception_tree(error: BaseException, key: str) -> None:
    seen: set[int] = set()
    stack: list[BaseException | None] = [error]
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        assert key not in str(current)
        assert key not in repr(current)
        assert all(key not in repr(arg) for arg in current.args)
        stack.extend([current.__cause__, current.__context__])


def test_sends_only_the_masked_text_with_store_off_and_a_strict_schema() -> None:
    judge, opener = _judge(_response(["이도현"]))

    judge.find_names(MASKED)

    request, timeout = opener.requests[0]
    assert request.full_url == OPENAI_RESPONSES_URL
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == f"Bearer {KEY}"
    assert timeout == DEFAULT_TIMEOUT_SECONDS
    body = json.loads(request.data)
    assert body["input"] == MASKED
    assert body["model"] == DEFAULT_MODEL == "gpt-6-luna"
    assert body["store"] is False
    assert body["reasoning"] == {"effort": "none"}
    assert body["temperature"] == 0
    assert body["max_output_tokens"] > 0
    text_format = body["text"]["format"]
    assert text_format["type"] == "json_schema"
    assert text_format["strict"] is True
    assert text_format["schema"]["required"] == ["names"]
    assert text_format["schema"]["additionalProperties"] is False


def test_returns_only_names_that_appear_in_the_masked_text() -> None:
    # 글에 없는 이름(환각), 대괄호 라벨, 빈 값, 중복은 버린다.
    judge, _ = _judge(_response(["이도현", "김철수", "[이름]", "  ", "이도현"]))

    assert judge.find_names(MASKED) == ["이도현"]


def test_reads_the_message_after_reasoning_items() -> None:
    reasoning = {"type": "reasoning", "id": "rs_1", "summary": []}
    judge, _ = _judge(_response(["이도현"], extra_items=[reasoning]))

    assert judge.find_names(MASKED) == ["이도현"]


def test_blank_text_is_not_sent() -> None:
    judge, opener = _judge(_response([]))

    assert judge.find_names("   ") == []
    assert opener.requests == []


def test_text_over_the_backstop_is_rejected_before_sending() -> None:
    judge, opener = _judge(_response([]))

    with pytest.raises(NameJudgeError) as caught:
        judge.find_names("가" * (MAX_INPUT_CHARS + 1))

    assert caught.value.code == "input_too_long"
    assert opener.requests == []


@pytest.mark.parametrize(
    ("payload", "raw", "code"),
    [
        (
            _response(content=[{"type": "refusal", "refusal": "이도현은 말할 수 없습니다"}]),
            None,
            "refused",
        ),
        (_response(["이도현"], status="incomplete"), None, "incomplete"),
        ({"object": "response", "status": "completed", "output": []}, None, "empty_output"),
        (_response(content=[{"type": "output_text", "text": "이도현"}]), None, "bad_schema"),
        (
            _response(content=[{"type": "output_text", "text": '{"names": "이도현"}'}]),
            None,
            "bad_schema",
        ),
        (None, b"not json", "bad_response"),
        (None, b"x" * (64 * 1024 + 1), "response_too_large"),
    ],
    ids=["refused", "incomplete", "empty", "text", "names-not-list", "not-json", "too-large"],
)
def test_bad_responses_raise_a_code_without_text_or_model_output(payload, raw, code) -> None:
    judge, _ = _judge(payload, raw=raw)

    with pytest.raises(NameJudgeError) as caught:
        judge.find_names(MASKED)

    assert caught.value.code == code
    assert str(caught.value) == code
    assert "이도현" not in str(caught.value)
    _assert_no_attached_details(caught.value)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (_http_error(401), "auth"),
        (_http_error(429, {"error": {"code": "project_spend_limit_exceeded"}}), "spend_limit"),
        (_http_error(429, {"error": {"code": "rate_limit_exceeded"}}), "rate_limited"),
        (_http_error(302), "redirect"),
        (_http_error(500, {"error": {"message": "이도현 처리 중 오류"}}), "upstream"),
        (_http_error(400, {"error": {"message": MASKED}}), "http_error"),
        (urllib.error.URLError(TimeoutError("timed out")), "timeout"),
        (TimeoutError("timed out"), "timeout"),
        (urllib.error.URLError("connection refused"), "network"),
        # 응답을 읽다 끊기는 오류는 http.client.HTTPException 계열이라 OSError 그물에 걸리지 않았다(#625).
        (http.client.IncompleteRead(b"partial"), "network"),
        (http.client.BadStatusLine("bad status"), "network"),
        # 429 에러 본문을 읽다 끊겨도 같은 그물에 걸려야 한다. 본문은 지출 한도 구분에만 쓴다(#625).
        (_http_error_with_broken_body(429), "rate_limited"),
    ],
)
def test_transport_errors_become_codes_without_details(error, code) -> None:
    judge, _ = _judge(raw=b"", error=error)

    with pytest.raises(NameJudgeError) as caught:
        judge.find_names(MASKED)

    assert caught.value.code == code
    assert "이도현" not in str(caught.value)
    assert KEY not in str(caught.value)
    _assert_no_attached_details(caught.value)


def test_default_opener_does_not_follow_redirects() -> None:
    judge = OpenAINameJudge(KEY)

    assert any(isinstance(handler, _NoRedirect) for handler in judge._opener.handlers)


def test_redirects_are_not_followed() -> None:
    # 따라가면 Authorization 헤더(키)가 다른 주소로 갈 수 있다.
    request = urllib.request.Request(OPENAI_RESPONSES_URL, headers={"Authorization": "Bearer x"})

    assert (
        _NoRedirect().redirect_request(request, None, 302, "Found", {}, "https://evil.example/")
        is None
    )


def test_api_key_is_not_in_repr() -> None:
    judge, _ = _judge(_response([]))

    assert KEY not in repr(judge)


def test_empty_key_is_rejected() -> None:
    with pytest.raises(ValueError):
        OpenAINameJudge("  ")


@pytest.mark.parametrize(
    "bad_key",
    [
        "test-key\nX-Injected: 1",
        "test-key한",
        "test-key\u200b",
    ],
    ids=["newline", "non-ascii", "zero-width-space"],
)
def test_invalid_api_key_is_rejected_without_leaking_the_key(bad_key: str) -> None:
    with pytest.raises(ValueError) as caught:
        OpenAINameJudge(bad_key)

    assert str(caught.value) == "OpenAI API key contains invalid characters"
    _assert_key_not_in_exception_tree(caught.value, bad_key)


def test_from_env_is_none_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert openai_name_judge_from_env() is None

    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    assert openai_name_judge_from_env() is None


@pytest.mark.parametrize(
    "bad_key",
    [
        "test-key\nX-Injected: 1",
        "test-key한",
        "test-key\u200b",
    ],
    ids=["newline", "non-ascii", "zero-width-space"],
)
def test_from_env_disables_judge_for_invalid_keys(
    monkeypatch: pytest.MonkeyPatch,
    bad_key: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", bad_key)

    assert openai_name_judge_from_env() is None


def test_from_env_reads_the_key_and_optional_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("MASKINGTAPE_API_OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("MASKINGTAPE_API_OPENAI_TIMEOUT_SECONDS", "7.5")

    judge = openai_name_judge_from_env()

    assert judge is not None
    assert judge.model == "gpt-test"
    assert judge.timeout == 7.5


def test_from_env_ignores_a_bad_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("MASKINGTAPE_API_OPENAI_TIMEOUT_SECONDS", "-3")

    judge = openai_name_judge_from_env()

    assert judge is not None
    assert judge.model == DEFAULT_MODEL
    assert judge.timeout == DEFAULT_TIMEOUT_SECONDS
