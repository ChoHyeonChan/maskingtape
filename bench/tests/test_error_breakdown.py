# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""error_breakdown.py(#612)의 미탐·오탐 분해 검증.

core 탐지기 동작에 기대지 않도록, 원하는 구간을 그대로 돌려주는 가짜 탐지기를 쓴다.
"""

from __future__ import annotations

from pathlib import Path

from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.error_breakdown import (
    ErrorBreakdown,
    breakdown_errors,
    format_breakdown_table,
    markdown_breakdown_table,
)
from bench.evaluators.evaluate import evaluate, load_dataset, write_markdown_report

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"


class _FixedDetector(Detector):
    """정해 둔 (종류, 시작, 끝)을 그대로 탐지 결과로 돌려준다."""

    def __init__(self, spans: list[tuple[str, int, int]]) -> None:
        self.spans = spans

    def detect(self, text: str) -> list[Detection]:
        return [Detection(kind=k, start=s, end=e, text=text[s:e], confidence=1.0) for k, s, e in self.spans]


def _run(text: str, gold: list[tuple[str, int, int]], pred: list[tuple[str, int, int]]) -> dict[str, ErrorBreakdown]:
    rows = [{"text": text, "labels": [{"kind": k, "start": s, "end": e} for k, s, e in gold]}]
    return breakdown_errors(rows, Pipeline(detectors=[_FixedDetector(pred)]))


def test_exact_match_is_tp_with_no_errors():
    result = _run("환자 권연의 생년월일", [("name", 3, 5)], [("name", 3, 5)])["name"]
    assert (result.tp, result.fn, result.fp) == (1, 0, 0)


def test_wider_prediction_is_covered_fn_and_boundary_fp():
    """정답 '권연'을 '권연의'로 한 글자 더 가렸다 — 유출은 없고 경계만 다르다."""
    result = _run("환자 권연의 생년월일", [("name", 3, 5)], [("name", 3, 6)])["name"]
    assert (result.fn_covered, result.fn_partial, result.fn_missed) == (1, 0, 0)
    assert (result.fp_boundary, result.fp_spurious) == (1, 0)
    assert result.leak_recall == 1.0


def test_narrower_prediction_is_partial_leak():
    """정답은 '123 4층'까지인데 '123'까지만 가렸다 — 남은 글자가 유출이다."""
    result = _run("테헤란로 123 4층", [("address", 0, 11)], [("address", 0, 8)])["address"]
    assert (result.fn_covered, result.fn_partial, result.fn_missed) == (0, 1, 0)
    assert result.fp_boundary == 1
    assert result.leak_recall == 0.0


def test_no_overlap_is_missed_and_spurious():
    result = _run("남원 팀장이 보고했습니다", [("name", 0, 2)], [("name", 7, 9)])["name"]
    assert (result.fn_covered, result.fn_partial, result.fn_missed) == (0, 0, 1)
    assert (result.fp_boundary, result.fp_spurious) == (0, 1)


def test_two_predictions_that_jointly_cover_the_gold_count_as_covered():
    """파이프라인은 겹치는 탐지를 합치므로, 맞닿지 않게 한 글자 겹쳐서가 아니라 이어 붙여 덮는다."""
    result = _run("abcdef", [("name", 0, 6)], [("name", 0, 3), ("phone", 3, 6)])
    assert result["name"].fn_covered == 1


def test_covered_by_a_different_kind_is_still_covered():
    """주소로 가려졌든 이름으로 가려졌든 글자는 안 보인다. 미탐은 정답 종류에, 오탐은 예측 종류에 센다."""
    result = _run("110123456789", [("account", 0, 12)], [("driver_license", 0, 12)])
    assert result["account"].fn_covered == 1
    assert result["driver_license"].fp_boundary == 1
    assert result["__overall__"].leak_recall == 1.0


def test_leak_recall_is_zero_not_divide_error_when_no_gold():
    assert ErrorBreakdown().leak_recall == 0.0
    assert ErrorBreakdown(fp_spurious=3).leak_recall == 0.0


def test_breakdown_sums_match_evaluate_counts_on_committed_dataset():
    """분해는 기존 집계를 다시 나눈 것일 뿐이다 — 종류마다 tp·fn·fp가 evaluate()와 같아야 한다."""
    rows = load_dataset(_DATASETS / "synth_v1.jsonl")[:150]
    pipeline = Pipeline()
    counts = evaluate(rows, pipeline)
    breakdown = breakdown_errors(rows, pipeline)
    assert set(counts) == set(breakdown)
    for kind, c in counts.items():
        b = breakdown[kind]
        assert (b.tp, b.fn, b.fp) == (c.tp, c.fn, c.fp), kind


def test_tables_show_every_group_and_overall():
    results = _run("환자 권연의 생년월일", [("name", 3, 5)], [("name", 3, 6)])
    console = format_breakdown_table(results)
    markdown = markdown_breakdown_table(results)
    assert "name" in console and "overall" in console and "leak_recall" in console
    assert "| name | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 1.000 |" in markdown
    assert "**overall**" in markdown
    assert "__overall__" in results  # 표를 만든 뒤에도 호출자의 결과를 건드리지 않는다


def test_markdown_report_appends_breakdown_only_when_given(tmp_path: Path):
    rows = [{"text": "010-1234-5678", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    pipeline = Pipeline()
    kind_results = evaluate(rows, pipeline)

    without = tmp_path / "without.md"
    write_markdown_report(without, Path("dummy.jsonl"), 1, kind_results, dict(kind_results))
    assert "미탐·오탐 분해" not in without.read_text(encoding="utf-8")

    with_breakdown = tmp_path / "with.md"
    write_markdown_report(
        with_breakdown, Path("dummy.jsonl"), 1, kind_results, dict(kind_results), breakdown_errors(rows, pipeline)
    )
    assert "## 미탐·오탐 분해 (유출 기준)" in with_breakdown.read_text(encoding="utf-8")
