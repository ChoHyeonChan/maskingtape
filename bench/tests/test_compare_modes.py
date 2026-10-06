# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""compare_modes.py(#548)의 캐시·집계 검증.

하이브리드는 로컬 Ollama가 있어야 돌아서, 여기서는 정해 둔 구간을 돌려주는 가짜 탐지기로
파이프라인을 만든다. Ollama 없이도 테스트가 돈다.
"""

from __future__ import annotations

import pytest
from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.compare_modes import CachedPipeline, build_pipeline, format_report, run_mode


class _CountingDetector(Detector):
    """정해 둔 구간을 돌려주고, 몇 번 불렸는지 센다."""

    kind = "fixed"

    def __init__(self, spans: dict[str, list[tuple[str, int, int]]]) -> None:
        self.spans = spans
        self.calls = 0

    def detect(self, text: str) -> list[Detection]:
        self.calls += 1
        return [
            Detection(kind=k, start=s, end=e, text=text[s:e], confidence=1.0, detector="fixed")
            for k, s, e in self.spans.get(text, [])
        ]


def test_cached_pipeline_scans_each_text_once():
    det = _CountingDetector({"a": [("name", 0, 1)]})
    cached = CachedPipeline(Pipeline(detectors=[det]))
    assert cached.scan("a") == cached.scan("a")
    assert cached.scans == 1 and det.calls == 1


def test_run_mode_scores_once_per_document_and_reports_leak_recall():
    """evaluate()와 breakdown_errors()가 각자 스캔해도 core는 문서마다 한 번만 불린다."""
    texts = {
        "고객 김민준님": [("name", 3, 6)],  # 적중
        "환자 권연의 기록": [("name", 3, 6)],  # 정답 '권연'보다 한 글자 더 — 가려짐
        "남원 팀장": [],  # 완전 미탐
    }
    rows = [
        {"text": "고객 김민준님", "labels": [{"kind": "name", "start": 3, "end": 6}]},
        {"text": "환자 권연의 기록", "labels": [{"kind": "name", "start": 3, "end": 5}]},
        {"text": "남원 팀장", "labels": [{"kind": "name", "start": 0, "end": 2}]},
    ]
    det = _CountingDetector(texts)
    result = run_mode(rows, Pipeline(detectors=[det]))
    assert det.calls == len(rows)
    assert (result.name.tp, result.name.fp, result.name.fn) == (1, 1, 2)
    assert result.name_leak_recall == pytest.approx(2 / 3)
    assert result.seconds_per_doc >= 0


def test_build_pipeline_rejects_unknown_mode():
    assert build_pipeline("rule", "unused").detectors
    with pytest.raises(ValueError):
        build_pipeline("cloud", "unused")


def test_format_report_names_the_model_and_every_row():
    rows = [{"text": "고객 김민준님", "labels": [{"kind": "name", "start": 3, "end": 6}]}]
    r = run_mode(rows, Pipeline(detectors=[_CountingDetector({"고객 김민준님": [("name", 3, 6)]})]))
    report = format_report({"synth_v1": {"rule": r, "hybrid": r}}, "test-model")
    assert "test-model" in report
    assert report.count("synth_v1") == 2
