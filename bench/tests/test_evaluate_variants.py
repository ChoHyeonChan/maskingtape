# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""evaluate_variants.py의 태그별 재현율 집계 검증."""

from __future__ import annotations

from maskingtape.pipeline import Pipeline

from bench.evaluators.evaluate_variants import TagCounts, evaluate_variants


def test_tag_counts_recall():
    c = TagCounts(tp=3, fn=1)
    assert c.recall == 0.75


def test_tag_counts_recall_is_zero_not_divide_error_when_empty():
    assert TagCounts().recall == 0.0


def test_evaluate_variants_groups_by_tag_and_counts_fp():
    rows = [
        {"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}], "variant_tag": "a"},
        {"text": "김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}], "variant_tag": "b"},
    ]
    per_tag, total_fp = evaluate_variants(rows, Pipeline(detectors=[]))
    assert per_tag["a"].fn == 1 and per_tag["a"].tp == 0
    assert per_tag["b"].fn == 1 and per_tag["b"].tp == 0
    assert total_fp == 0


def test_evaluate_variants_counts_extra_detections_as_fp():
    rows = [{"text": "고객 김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 3, "end": 6}], "variant_tag": "a"}]
    per_tag, total_fp = evaluate_variants(rows, Pipeline())
    assert per_tag["a"].tp == 1
    assert total_fp == 0
