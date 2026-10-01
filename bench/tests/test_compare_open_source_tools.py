# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""compare_open_source_tools.py의 공통 채점·매핑 로직을 확인한다."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bench.evaluators.compare_open_source_tools import (
    build_tool_runs,
    evaluate_predictor,
    format_markdown_report,
    scrubadub_spans,
)
from bench.evaluators.evaluate import Span


def test_evaluate_predictor_uses_exact_span_match():
    rows = [
        {
            "text": "email hong@example.com phone 010-1234-5678",
            "labels": [
                {"kind": "email", "start": 6, "end": 22},
                {"kind": "phone", "start": 29, "end": 42},
            ],
        }
    ]

    def predict(_: str) -> set[Span]:
        return {
            Span(kind="email", start=6, end=22),
            Span(kind="phone", start=30, end=42),
            Span(kind="card", start=0, end=4),
        }

    results = evaluate_predictor(rows, predict)
    assert results["email"].tp == 1
    assert results["phone"].fn == 1
    assert results["phone"].fp == 1
    assert results["card"].fp == 1
    assert results["__overall__"].tp == 1
    assert results["__overall__"].fp == 2
    assert results["__overall__"].fn == 1


def test_scrubadub_spans_maps_only_supported_entity_types():
    filths = [
        SimpleNamespace(type="email", beg=0, end=16),
        SimpleNamespace(type="phone", beg=17, end=30),
        SimpleNamespace(type="credit_card", beg=31, end=50),
        SimpleNamespace(type="social_security_number", beg=51, end=62),
    ]

    assert scrubadub_spans(filths) == {
        Span(kind="email", start=0, end=16),
        Span(kind="phone", start=17, end=30),
        Span(kind="card", start=31, end=50),
    }


def test_format_markdown_report_contains_mapping_and_per_tool_tables():
    rows = [{"text": "hong@example.com", "labels": [{"kind": "email", "start": 0, "end": 16}]}]
    results = {"demo": evaluate_predictor(rows, lambda _: {Span("email", 0, 16)})}
    tool = SimpleNamespace(
        name="demo",
        version="1.0",
        license="MIT",
        homepage="https://example.com",
        kind_map={"EMAIL": "email"},
    )

    report = format_markdown_report(
        dataset_path="bench/datasets/synth_v1.jsonl",
        doc_count=1,
        tool_runs=[tool],
        results_by_tool=results,
    )

    assert "오픈소스 PII 도구 비교 리포트" in report
    assert "| demo | EMAIL | email |" in report
    assert "## demo kind별 결과" in report
    assert "| **overall** | **1.000** | **1.000**" in report


def test_build_tool_runs_rejects_unknown_tool():
    with pytest.raises(ValueError, match="알 수 없는 비교 도구"):
        build_tool_runs(["does-not-exist"])
