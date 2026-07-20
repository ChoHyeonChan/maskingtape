"""evaluate.py의 precision/recall/F1 집계 로직 검증 (core 탐지기와 무관한 순수 계산 테스트)."""

from __future__ import annotations

from bench.evaluate import Counts, Span, evaluate
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
