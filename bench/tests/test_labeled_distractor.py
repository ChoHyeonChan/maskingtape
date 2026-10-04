# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""사업자등록번호 라벨 바로 뒤의 체크섬 오류 번호를 정답으로 채점하는지 검증한다(#650).

core는 #607(PR #646)부터 라벨이 번호 바로 앞에 있으면 체크섬이 틀린 번호도 가린다. 생성기가 그
자리의 오답지를 계속 비개인정보로 두면, 엔진이 맞게 가린 것이 오탐으로 집계된다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from bench.generator.documents import _labeled_distractor_kind

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"
_LABELED_BIZ_RE = re.compile(r"(?:사업자 ?등록번호|사업자번호)[ \t]{0,3}[:：]?[ \t]{0,3}(\d{3}-\d{2}-\d{5})")


@pytest.mark.parametrize("before", ["사업자등록번호 ", "사업자등록번호: ", "사업자 등록번호 : ", "거래처 사업자번호 "])
def test_business_number_right_after_label_is_biz_reg(before):
    assert _labeled_distractor_kind(before, "763-29-81658") == "biz_reg"


@pytest.mark.parametrize(
    ("before", "value"),
    [
        ("사업자등록번호는 ", "763-29-81658"),  # 조사가 끼면 core도 라벨로 보지 않는다
        ("주문번호 ", "763-29-81658"),  # 라벨이 다르다
        ("사업자등록번호 ", "2024-0101-1234"),  # 사업자번호 모양이 아니다
        ("사업자등록번호 ", "06236"),
    ],
)
def test_other_distractors_stay_unlabeled(before, value):
    assert _labeled_distractor_kind(before, value) is None


@pytest.mark.parametrize("name", ["synth_v1.jsonl", "synth_v2.jsonl"])
def test_committed_datasets_label_every_business_number_after_label(name):
    """커밋된 v1·v2에서 라벨 바로 뒤의 사업자번호 모양 값은 전부 biz_reg 정답이어야 한다."""
    with (_DATASETS / name).open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    checked = 0
    for row in rows:
        labeled = {(lb["start"], lb["end"]) for lb in row["labels"] if lb["kind"] == "biz_reg"}
        for m in _LABELED_BIZ_RE.finditer(row["text"]):
            assert m.span(1) in labeled, row["text"]
            checked += 1
    assert checked > 0
