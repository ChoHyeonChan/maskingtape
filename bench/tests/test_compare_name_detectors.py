"""compare_name_detectors.py의 비교 로직을 확인한다."""

from __future__ import annotations

from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.compare_name_detectors import evaluate_name_only, format_comparison, try_evaluate_llm_name
from bench.evaluators.evaluate import Counts


class _FixedNameDetector(Detector):
    """테스트 전용 — 항상 [0, len(text)) 구간을 name으로 탐지하는 가짜 탐지기."""

    kind = "name"

    def detect(self, text: str) -> list[Detection]:
        return [Detection(kind=self.kind, start=0, end=len(text), text=text, confidence=1.0, detector="fake")]


class _NoopAnonymizer(Anonymizer):
    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        return text


class _FailingDetector(Detector):
    """테스트 전용 — LLMNameDetector가 Ollama 연결 실패 시 내는 RuntimeError를 흉내낸다."""

    kind = "name"

    def detect(self, text: str) -> list[Detection]:
        raise RuntimeError("로컬 Ollama에 연결하지 못했습니다(가짜 에러 — 테스트용)")


def test_evaluate_name_only_extracts_name_row():
    rows = [{"text": "김철수", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    pipeline = Pipeline(detectors=[_FixedNameDetector()], anonymizer=_NoopAnonymizer())
    counts = evaluate_name_only(rows, pipeline)
    assert counts.tp == 1
    assert counts.fp == 0
    assert counts.fn == 0


def test_evaluate_name_only_returns_empty_counts_when_no_name_labels():
    rows = [{"text": "010-1234-5678", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    counts = evaluate_name_only(rows, Pipeline(detectors=[]))
    assert counts.tp == 0
    assert counts.fp == 0
    assert counts.fn == 0


def test_try_evaluate_llm_name_returns_none_on_runtime_error():
    """LLM 탐지기가 (Ollama 연결 실패 등으로) RuntimeError를 내면 예외 대신 None을 반환해야 한다.

    실제 Ollama 유무에 의존하지 않도록, 가짜 탐지기로 연결 실패 상황을 직접 재현한다.
    """
    rows = [{"text": "김철수님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    pipeline = Pipeline(detectors=[_FailingDetector()], anonymizer=_NoopAnonymizer())
    result = try_evaluate_llm_name(rows, pipeline)
    assert result is None


def test_try_evaluate_llm_name_returns_counts_on_success():
    rows = [{"text": "김철수", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    pipeline = Pipeline(detectors=[_FixedNameDetector()], anonymizer=_NoopAnonymizer())
    result = try_evaluate_llm_name(rows, pipeline)
    assert result is not None
    assert result.tp == 1


def test_format_comparison_shows_unavailable_message_when_llm_is_none():
    report = format_comparison(Counts(tp=1, fp=0, fn=0), None)
    assert "규칙판" in report
    assert "하이브리드" in report
    assert "사용 불가" in report


def test_format_comparison_shows_both_rows_when_llm_counts_present():
    report = format_comparison(Counts(tp=1, fp=0, fn=0), Counts(tp=2, fp=0, fn=0))
    assert "규칙판" in report
    assert "하이브리드" in report
    assert "사용 불가" not in report
