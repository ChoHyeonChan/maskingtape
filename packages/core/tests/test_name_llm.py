"""LLM 이름 탐지기 테스트 — 합성 데이터만 사용.

CI에는 Ollama가 없으므로 가짜 client를 주입해 순수 로직(위치 변환·환각 방어)만 검증한다.
실제 모델 호출은 로컬에서 `maskingtape --llm`으로 확인한다.
"""

import json

import pytest

from maskingtape.detectors import name_llm
from maskingtape.detectors.name_llm import LLMNameDetector


def detector(names: list[str]) -> LLMNameDetector:
    """LLM이 names를 돌려준다고 가정한 탐지기."""
    return LLMNameDetector(client=lambda _text: names)


def test_converts_model_names_into_positions():
    text = "고객 김철수님께 연락드렸습니다."
    found = detector(["김철수"]).detect(text)
    assert len(found) == 1
    assert found[0].kind == "name"
    assert found[0].text == "김철수"
    assert text[found[0].start : found[0].end] == "김철수"
    assert found[0].confidence == 0.9


def test_detects_every_occurrence_of_the_same_name():
    text = "김영희 담당자에게 전달했고, 김영희 확인 완료."
    found = detector(["김영희"]).detect(text)
    assert len(found) == 2
    assert all(text[d.start : d.end] == "김영희" for d in found)


def test_ignores_hallucinated_names_not_present_in_text():
    # 모델이 원문에 없는 이름을 지어내도 버린다
    found = detector(["박서준"]).detect("고객 김철수님께 연락드렸습니다.")
    assert found == []


def test_returns_nothing_when_model_finds_no_names():
    assert detector([]).detect("이용 안내: 회원 가입 후 사용하세요.") == []


def test_skips_empty_or_non_string_entries():
    found = detector(["", None, "김철수"]).detect("고객 김철수님")  # type: ignore[list-item]
    assert len(found) == 1
    assert found[0].text == "김철수"


def test_blank_text_does_not_call_the_model():
    called = False

    def client(_text: str) -> list[str]:
        nonlocal called
        called = True
        return ["김철수"]

    assert LLMNameDetector(client=client).detect("   ") == []
    assert not called


def test_connection_failure_raises_actionable_error():
    # 실제 호출 경로: 아무도 듣지 않는 포트로 보내 연결 실패를 만든다
    d = LLMNameDetector(host="http://127.0.0.1:9", timeout=1.0)
    with pytest.raises(RuntimeError, match="Ollama"):
        d.detect("고객 김철수님께 연락드렸습니다.")


class _FakeResponse:
    """urlopen 컨텍스트 매니저 흉내 — 모델 응답 본문만 돌려준다."""

    def __init__(self, response_field: str) -> None:
        self._body = json.dumps({"response": response_field}).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _detector_with_model_response(monkeypatch, response_field: str) -> LLMNameDetector:
    monkeypatch.setattr(
        name_llm.urllib.request, "urlopen", lambda *_a, **_kw: _FakeResponse(response_field)
    )
    return LLMNameDetector()


def test_empty_json_object_means_no_names(monkeypatch):
    # 실측: 이름이 없으면 모델이 {"names": []} 대신 {}만 주기도 한다 — 오류가 아니라 빈 결과다
    d = _detector_with_model_response(monkeypatch, "{}")
    assert d.detect("작성자 정보를 확인하세요.") == []


def test_names_key_is_used_when_present(monkeypatch):
    d = _detector_with_model_response(monkeypatch, '{"names": ["김철수"]}')
    found = d.detect("고객 김철수님")
    assert [f.text for f in found] == ["김철수"]


def test_non_list_names_raises(monkeypatch):
    d = _detector_with_model_response(monkeypatch, '{"names": "김철수"}')
    with pytest.raises(RuntimeError, match="이름 목록"):
        d.detect("고객 김철수님")
