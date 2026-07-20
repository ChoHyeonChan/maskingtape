"""evaluate.py의 precision/recall/F1 집계 로직 검증 (core 탐지기와 무관한 순수 계산 테스트)."""

from __future__ import annotations

from pathlib import Path

from bench.evaluate import Counts, Span, evaluate, evaluate_by_difficulty, write_markdown_report
from maskingtape.pipeline import Pipeline


def test_counts_precision_recall_f1():
    c = Counts(tp=3, fp=1, fn=2)
    assert c.precision == 3 / 4
    assert c.recall == 3 / 5
    assert round(c.f1, 4) == round(2 * (3 / 4) * (3 / 5) / ((3 / 4) + (3 / 5)), 4)


def test_counts_all_zero_is_zero_not_divide_error():
    c = Counts()
    assert c.precision == 0.0
    assert c.recall == 0.0
    assert c.f1 == 0.0


def test_evaluate_perfect_match_on_known_pattern():
    rows = [{"text": "010-1234-5678", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    results = evaluate(rows, Pipeline())
    overall = results["__overall__"]
    assert overall.tp == 1
    assert overall.fp == 0
    assert overall.fn == 0


def test_evaluate_counts_false_negative_for_undetected_kind():
    rows = [{"text": "김민준", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    results = evaluate(rows, Pipeline())
    assert results["name"].fn == 1
    assert results["name"].tp == 0


def test_span_is_hashable_for_set_operations():
    a = Span(kind="phone", start=0, end=5)
    b = Span(kind="phone", start=0, end=5)
    assert a == b
    assert {a, b} == {a}


def test_evaluate_by_difficulty_groups_correctly():
    rows = [
        {"text": "010-1234-5678", "labels": [{"kind": "phone", "start": 0, "end": 13}], "difficulty": "easy"},
        {"text": "01098765432", "labels": [{"kind": "phone", "start": 0, "end": 11}], "difficulty": "hard"},
        {"text": "회의는 내일입니다.", "labels": [], "difficulty": "negative"},
    ]
    results = evaluate_by_difficulty(rows, Pipeline())
    assert results["easy"].tp == 1
    assert results["hard"].tp == 1
    assert results["negative"].tp == 0
    assert results["negative"].fp == 0
    assert results["__overall__"].tp == 2


def test_evaluate_by_difficulty_falls_back_to_unknown_for_legacy_rows():
    """difficulty 필드가 없는 구형 데이터셋도 평가가 깨지지 않아야 한다 (하위 호환)."""
    rows = [{"text": "010-1234-5678", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    results = evaluate_by_difficulty(rows, Pipeline())
    assert results["unknown"].tp == 1


def test_write_markdown_report_creates_readable_file(tmp_path: Path):
    rows = [{"text": "010-1234-5678", "labels": [{"kind": "phone", "start": 0, "end": 13}], "difficulty": "easy"}]
    pipeline = Pipeline()
    kind_results = evaluate(rows, pipeline)
    difficulty_results = evaluate_by_difficulty(rows, pipeline)

    report_path = tmp_path / "report.md"
    write_markdown_report(report_path, Path("dummy.jsonl"), len(rows), kind_results, difficulty_results)

    content = report_path.read_text(encoding="utf-8")
    assert "phone" in content
    assert "easy" in content
    assert "overall" in content.lower()
