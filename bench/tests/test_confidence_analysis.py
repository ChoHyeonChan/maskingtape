"""confidence_analysis.py의 임계값별 집계 로직을 확인한다."""

from __future__ import annotations

from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.confidence_analysis import evaluate_at_threshold, evaluate_by_threshold, format_threshold_report


class _FixedConfidenceDetector(Detector):
    """테스트 전용 — 항상 같은 구간을 정해진 confidence로 탐지하는 가짜 탐지기."""

    kind = "phone"

    def __init__(self, confidence: float) -> None:
        self.confidence = confidence

    def detect(self, text: str) -> list[Detection]:
        return [Detection(kind=self.kind, start=0, end=len(text), text=text, confidence=self.confidence, detector="fake")]


class _NoopAnonymizer(Anonymizer):
    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        return text


def _pipeline_with_confidence(confidence: float) -> Pipeline:
    return Pipeline(detectors=[_FixedConfidenceDetector(confidence)], anonymizer=_NoopAnonymizer())


def test_low_threshold_keeps_low_confidence_prediction():
    rows = [{"text": "abc", "labels": [{"kind": "phone", "start": 0, "end": 3}]}]
    result = evaluate_at_threshold(rows, _pipeline_with_confidence(0.6), threshold=0.5)
    assert result.tp == 1
    assert result.fp == 0


def test_high_threshold_drops_low_confidence_prediction_and_counts_as_miss():
    """임계값보다 낮은 confidence 예측은 버려지므로, 정답을 놓친 것(fn)으로 집계돼야 한다."""
    rows = [{"text": "abc", "labels": [{"kind": "phone", "start": 0, "end": 3}]}]
    result = evaluate_at_threshold(rows, _pipeline_with_confidence(0.6), threshold=0.9)
    assert result.tp == 0
    assert result.fn == 1


def test_evaluate_by_threshold_returns_one_result_per_threshold():
    rows = [{"text": "abc", "labels": [{"kind": "phone", "start": 0, "end": 3}]}]
    results = evaluate_by_threshold(rows, _pipeline_with_confidence(0.85), thresholds=(0.5, 0.9))
    assert set(results.keys()) == {0.5, 0.9}
    assert results[0.5].tp == 1  # 0.85 >= 0.5 → 살아남음
    assert results[0.9].tp == 0  # 0.85 < 0.9 → 버려짐


def test_precision_improves_or_stays_same_as_threshold_rises_on_real_core():
    """실제 core(phone/rrn)로도 임계값을 올리면 정밀도가 나빠지지 않아야 한다 (일반적 기대)."""
    rows = [
        {"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]},
        {"text": "01098765432로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 11}]},
    ]
    results = evaluate_by_threshold(rows, Pipeline(), thresholds=(0.0, 1.0))
    assert results[0.0].precision <= results[1.0].precision or results[1.0].tp + results[1.0].fp == 0


def test_format_threshold_report_lists_all_thresholds_sorted():
    rows = [{"text": "abc", "labels": []}]
    results = evaluate_by_threshold(rows, _pipeline_with_confidence(0.9), thresholds=(0.9, 0.1, 0.5))
    report = format_threshold_report(results)
    idx_01 = report.index("0.10")
    idx_05 = report.index("0.50")
    idx_09 = report.index("0.90")
    assert idx_01 < idx_05 < idx_09
