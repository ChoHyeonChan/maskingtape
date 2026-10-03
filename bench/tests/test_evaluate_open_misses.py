# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""evaluate_open_misses.py의 이슈별·태그별 집계 검증."""

from __future__ import annotations

from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.evaluate_open_misses import (
    MissCounts,
    by_issue,
    evaluate_open_misses,
    format_report,
)


def _row(text: str, labels: list[dict], tag: str = "t", issue: int = 1) -> dict:
    return {"text": text, "labels": labels, "miss_tag": tag, "issue": issue}


class _FixedDetector(Detector):
    """정해 둔 구간만 돌려주는 가짜 탐지기.

    집계 테스트가 core의 실제 탐지 결과에 기대면, core가 미탐을 고칠 때마다 '부분 적중'
    예시가 '완전 적중'으로 바뀌어 테스트가 깨진다(#624가 주소 꼬리를 고치자 그랬다).
    """

    kind = "fixed"

    def __init__(self, spans: dict[str, list[tuple[str, int, int]]]) -> None:
        self.spans = spans

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(kind=kind, start=start, end=end, text=text[start:end], confidence=1.0, detector="fixed")
            for kind, start, end in self.spans.get(text, [])
        ]


def test_miss_counts_recall_counts_only_exact_hits():
    assert MissCounts(tp=1, partial=1, miss=2).recall == 0.25


def test_miss_counts_recall_is_zero_not_divide_error_when_empty():
    assert MissCounts().recall == 0.0


def test_exact_hit_partial_and_miss_are_separated():
    rows = [
        # 완전 일치 — 예측이 정답 구간과 똑같다
        _row("고객 김민준님 안녕하세요.", [{"kind": "name", "start": 3, "end": 6}], tag="hit"),
        # 부분 — 정답은 층까지인데 예측은 번지까지만
        _row(
            "서울특별시 강남구 테헤란로 123 4층",
            [{"kind": "address", "start": 0, "end": 21}],
            tag="partial",
        ),
        # 미탐 — 탐지기가 없으면 겹치는 예측도 없다
        _row("010-1234-5678", [{"kind": "phone", "start": 0, "end": 13}], tag="miss"),
    ]
    fixed = _FixedDetector(
        {
            "고객 김민준님 안녕하세요.": [("name", 3, 6)],
            "서울특별시 강남구 테헤란로 123 4층": [("address", 0, 18)],
        }
    )
    per_tag, total_fp = evaluate_open_misses(rows[:2], Pipeline(detectors=[fixed]))
    assert (per_tag[(1, "hit")].tp, per_tag[(1, "hit")].partial, per_tag[(1, "hit")].miss) == (1, 0, 0)
    assert (per_tag[(1, "partial")].tp, per_tag[(1, "partial")].partial, per_tag[(1, "partial")].miss) == (0, 1, 0)
    assert total_fp == 0  # 부분 적중을 오탐으로 또 세지 않는다

    per_tag, _ = evaluate_open_misses(rows[2:], Pipeline(detectors=[]))
    assert (per_tag[(1, "miss")].tp, per_tag[(1, "miss")].partial, per_tag[(1, "miss")].miss) == (0, 0, 1)


def test_non_target_labels_are_left_out_of_recall_but_not_counted_as_fp():
    text = "고객 김민준님 안녕하세요."
    rows = [_row(text, [{"kind": "name", "start": 3, "end": 6, "target": False}])]
    per_tag, total_fp = evaluate_open_misses(rows, Pipeline())
    assert per_tag[(1, "t")].total == 0
    assert total_fp == 0


def test_prediction_outside_every_gold_label_is_fp():
    rows = [_row("고객 김민준님, 010-1234-5678", [{"kind": "name", "start": 3, "end": 6}])]
    _, total_fp = evaluate_open_misses(rows, Pipeline())
    assert total_fp == 1  # 전화번호는 정답 라벨에 없다


def test_by_issue_sums_tags_of_the_same_issue():
    per_tag = {(603, "a"): MissCounts(tp=1, miss=1), (603, "b"): MissCounts(partial=2), (604, "c"): MissCounts(tp=3)}
    per_issue = by_issue(per_tag)
    assert (per_issue[603].tp, per_issue[603].partial, per_issue[603].miss) == (1, 2, 1)
    assert per_issue[604].recall == 1.0


def test_format_report_lists_each_tag_issue_subtotal_and_overall():
    report = format_report({(603, "a"): MissCounts(tp=1, miss=1), (604, "c"): MissCounts(tp=3)}, total_fp=2)
    assert "#603" in report and "#604" in report and "이슈 소계" in report
    assert "전체" in report and "오탐(fp): 2건" in report
