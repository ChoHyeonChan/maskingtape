# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""열린 미탐 세트(#610) 생성기 검증.

이 세트의 target 라벨은 core가 **아직 못 잡는** 자리다. 그 "못 잡는다"를 테스트로 고정하지
않는다 — core PR이 미탐을 고칠 때마다 이 테스트가 깨지면 고치는 쪽에 짐이 된다. 여기서는
생성기가 약속한 것(라벨 위치, 재현성, 받침에 맞는 조사)과, target이 아닌 라벨은 지금
core가 잡는다는 전제만 확인한다.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest
from maskingtape.pipeline import Pipeline

from bench.generate_open_misses import V1_DATASET_NAME, V1_PER_TAG, V1_SEED, main
from bench.generator.entities import _biz_reg_check_digit, _luhn_check_digit
from bench.generator.open_misses import (
    FIXED_ISSUES,
    MISS_TAGS,
    _has_batchim,
    _josa,
    _josa_ro,
    generate_open_misses_dataset,
)

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_batchim_and_josa_helpers():
    assert _has_batchim("민") and not _has_batchim("수")
    assert _josa("김민준", "이", "가") == "이"
    assert _josa("김민수", "이", "가") == "가"
    # 받침이 없거나 ㄹ 받침이면 '로', 그 밖의 받침이면 '으로'
    assert _josa_ro("박지우") == "로"
    assert _josa_ro("최하율") == "로"
    assert _josa_ro("이서연") == "으로"


@pytest.mark.parametrize("tag_fn_name", sorted(MISS_TAGS))
def test_every_label_points_at_a_nonempty_slice_inside_the_text(tag_fn_name):
    rng = random.Random(f"test:{tag_fn_name}")
    for _ in range(30):
        doc = MISS_TAGS[tag_fn_name](rng)
        assert doc.labels, doc
        for label in doc.labels:
            assert 0 <= label["start"] < label["end"] <= len(doc.text), doc
            value = doc.text[label["start"] : label["end"]]
            assert value == value.strip(), f"라벨이 공백을 포함한다: {value!r}"


@pytest.mark.parametrize("tag_fn_name", sorted(MISS_TAGS))
def test_every_doc_has_at_least_one_target_label(tag_fn_name):
    """target이 하나도 없는 문서는 재현율에 아무 기여도 못 한다."""
    rng = random.Random(f"test:{tag_fn_name}")
    for _ in range(30):
        doc = MISS_TAGS[tag_fn_name](rng)
        assert any(label.get("target", True) for label in doc.labels), doc


@pytest.mark.parametrize("tag_fn_name", sorted(MISS_TAGS))
def test_non_target_labels_are_detected_by_current_core(tag_fn_name):
    """target이 아닌 라벨은 "지금도 잡히는 자리"라는 전제로 재현율에서 뺐다. 그 전제가
    깨지면(core가 되돌아가면) 이 세트의 수치가 실제보다 좋게 보이므로 여기서 잡는다."""
    rng = random.Random(f"test:{tag_fn_name}")
    pipeline = Pipeline()
    for _ in range(30):
        doc = MISS_TAGS[tag_fn_name](rng)
        pred = {(d.kind, d.start, d.end) for d in pipeline.scan(doc.text)}
        for label in doc.labels:
            if not label.get("target", True):
                assert (label["kind"], label["start"], label["end"]) in pred, doc.text


def test_bad_checksum_numbers_really_fail_their_checksum():
    """#607 태그는 "검증 숫자가 틀린 번호"여야 한다. 우연히 맞는 번호가 섞이면 지금도 잡혀서
    core가 아무것도 안 고쳤는데 재현율이 0보다 높게 나온다."""
    rows = generate_open_misses_dataset(1, per_tag=50)
    for row in rows:
        label = row["labels"][0]
        digits = row["text"][label["start"] : label["end"]].replace("-", "")
        if row["miss_tag"] == "card_label_bad_checksum":
            assert _luhn_check_digit(digits[:-1]) != digits[-1], row
        elif row["miss_tag"] == "biz_reg_label_bad_checksum":
            assert _biz_reg_check_digit(digits[:-1]) != digits[-1], row


def test_every_row_carries_issue_number_and_tag():
    rows = generate_open_misses_dataset(V1_SEED, per_tag=3)
    assert {row["miss_tag"] for row in rows} == {
        name.removeprefix("gen_") for name in MISS_TAGS
    }
    assert all(isinstance(row["issue"], int) and row["difficulty"] == "open_miss" for row in rows)


def test_generation_is_reproducible_from_seed():
    assert generate_open_misses_dataset(V1_SEED, per_tag=10) == generate_open_misses_dataset(V1_SEED, per_tag=10)


def test_committed_open_misses_v1_dataset_is_reproducible_from_seed():
    """커밋된 파일은 시드로 다시 만든 결과와 같아야 한다 — 손으로 고친 행이 섞이지 않게."""
    assert _load_rows(_DATASETS / V1_DATASET_NAME) == generate_open_misses_dataset(V1_SEED, per_tag=V1_PER_TAG)


def test_cli_writes_a_new_file(tmp_path, monkeypatch):
    target = tmp_path / "open_misses_small.jsonl"
    monkeypatch.setattr(sys, "argv", ["generate_open_misses", "--seed", "1", "--per-tag", "2", "--out", str(target)])
    main()
    rows = _load_rows(target)
    assert len(rows) == 2 * len(MISS_TAGS)
    assert rows == generate_open_misses_dataset(1, per_tag=2)


_FIXED_TAGS = sorted(name for name, gen in MISS_TAGS.items() if gen(random.Random(0)).issue in FIXED_ISSUES)


@pytest.mark.parametrize("tag_fn_name", _FIXED_TAGS)
def test_tags_of_fixed_issues_are_still_detected(tag_fn_name):
    """core가 고친 이슈(FIXED_ISSUES)의 모양은 지금 core가 전부 완전 일치로 잡아야 한다 — 되돌아가면
    실패한다(#653). 아직 안 고친 이슈의 태그는 여기서 보지 않으므로, core가 미탐을 고쳐도 깨지지 않는다."""
    rng = random.Random(f"fixed:{tag_fn_name}")
    pipeline = Pipeline()
    for _ in range(30):
        doc = MISS_TAGS[tag_fn_name](rng)
        pred = {(d.kind, d.start, d.end) for d in pipeline.scan(doc.text)}
        for label in doc.labels:
            assert (label["kind"], label["start"], label["end"]) in pred, (doc.issue, doc.text)


def test_fixed_issues_all_have_tags():
    issues = {MISS_TAGS[name](random.Random(0)).issue for name in MISS_TAGS}
    assert FIXED_ISSUES <= issues
