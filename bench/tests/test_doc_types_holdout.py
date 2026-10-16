# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 보고용 세트(#456)의 약속 검증.

보고용 세트가 지켜야 할 것은 셋이다. ① 같은 시드로 바이트 단위까지 재현된다. ② 이름 음절과 문서 틀이
조정용(`doc_types_v1`)과 다르다. ③ 라벨이 깨끗하다. core가 이 세트에서 얼마나 잡는지는 보지 않는다.
"""

from __future__ import annotations

import json
import random
import re
import sys
from itertools import pairwise
from pathlib import Path

import pytest

from bench.generate_doc_types_holdout import (
    HOLDOUT_DATASET_NAME,
    HOLDOUT_PER_TYPE,
    HOLDOUT_SEED,
    main,
)
from bench.generator.doc_types import DOC_TYPES, _has_batchim
from bench.generator.doc_types_holdout import (
    _HOLDOUT_SYLLABLES,
    _WORD_LIKE_NAMES,
    HOLDOUT_DOC_TYPES,
    generate_holdout_dataset,
)
from bench.generator.entities import _GIVEN_SYLLABLES

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"
_ALL_GENERATORS = [g for gens in HOLDOUT_DOC_TYPES.values() for g in gens]
_HANGUL_NAME_RE = re.compile(r"[가-힣]{2,4}")

# 판결문 양식이라 어느 판결문에나 있는 줄. 조정용과 겹쳐도 문서 틀을 베낀 게 아니다.
_SHARED_BOILERPLATE = {"주 문", "이 유", "판 결", "0. 판단", "판사 <name>", "<address>"}


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _line_frames(rows: list[dict]) -> set[str]:
    """개인정보 자리를 <종류>로, 숫자를 0으로 바꾼 줄 모음 — 문서 틀만 남긴다."""
    frames = set()
    for row in rows:
        text = row["text"]
        for lb in sorted(row["labels"], key=lambda lb: -lb["start"]):
            text = text[: lb["start"]] + f"<{lb['kind']}>" + text[lb["end"] :]
        frames |= {re.sub(r"\d", "0", line).strip() for line in text.split("\n")}
    return frames - {""}


def test_committed_dataset_is_reproducible_from_seed():
    rows = generate_holdout_dataset(HOLDOUT_SEED, per_type=HOLDOUT_PER_TYPE)
    assert _load_rows(_DATASETS / HOLDOUT_DATASET_NAME) == rows
    expected = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    assert (_DATASETS / HOLDOUT_DATASET_NAME).read_text(encoding="utf-8") == expected


def test_same_doc_types_as_tuning_set():
    assert set(HOLDOUT_DOC_TYPES) == set(DOC_TYPES)
    rows = generate_holdout_dataset(HOLDOUT_SEED, per_type=2)
    assert {row["doc_type"] for row in rows} == set(DOC_TYPES)
    assert all(row["split"] == "holdout" for row in rows)


def test_name_syllables_do_not_overlap_tuning_or_training_names():
    assert not set(_HOLDOUT_SYLLABLES) & set(_GIVEN_SYLLABLES)


def test_line_frames_differ_from_tuning_set():
    tuning = _line_frames(_load_rows(_DATASETS / "doc_types_v1.jsonl"))
    holdout = _line_frames(_load_rows(_DATASETS / HOLDOUT_DATASET_NAME))
    assert tuning & holdout <= _SHARED_BOILERPLATE, sorted(tuning & holdout - _SHARED_BOILERPLATE)


@pytest.mark.parametrize("gen", _ALL_GENERATORS, ids=lambda g: g.__name__)
def test_labels_are_clean_and_do_not_overlap(gen):
    rng = random.Random(f"holdout:{gen.__name__}")
    for _ in range(30):
        doc = gen(rng)
        assert any(lb["kind"] == "name" for lb in doc.labels)
        for lb in doc.labels:
            value = doc.text[lb["start"] : lb["end"]]
            assert value and value == value.strip(), (lb, doc.text)
            if lb["kind"] == "name":
                assert _HANGUL_NAME_RE.fullmatch(value), value
                assert value not in _WORD_LIKE_NAMES, value
        spans = sorted((lb["start"], lb["end"]) for lb in doc.labels)
        assert all(a_end <= b_start for (_, a_end), (b_start, _) in pairwise(spans))


def test_name_josa_follows_batchim():
    pairs = {"은": True, "는": False, "과": True, "와": False, "이": True, "가": False}
    for row in generate_holdout_dataset(HOLDOUT_SEED, per_type=20):
        for lb in row["labels"]:
            after = row["text"][lb["end"] : lb["end"] + 2]
            if lb["kind"] == "name" and len(after) == 2 and after[0] in pairs and after[1] == " ":
                name = row["text"][lb["start"] : lb["end"]]
                assert _has_batchim(name[-1]) == pairs[after[0]], (name, after)


def test_cli_writes_a_new_file(tmp_path, monkeypatch):
    target = tmp_path / "holdout_small.jsonl"
    monkeypatch.setattr(sys, "argv", ["generate_doc_types_holdout", "--seed", "1", "--per-type", "2", "--out", str(target)])
    main()
    assert _load_rows(target) == generate_holdout_dataset(1, per_type=2)
