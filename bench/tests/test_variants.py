# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""표기 변형 평가 세트(#531) 생성기 검증."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from maskingtape.pipeline import Pipeline

from bench.generate_variants import main
from bench.generator.variants import VARIANT_TAGS, generate_variants_dataset

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_every_generator_produces_exactly_one_gold_label():
    rng_rows = generate_variants_dataset(1, per_tag=5)
    for row in rng_rows:
        assert len(row["labels"]) == 1, row
        label = row["labels"][0]
        assert row["text"][label["start"] : label["end"]]


def test_generation_is_reproducible_from_seed():
    assert generate_variants_dataset(531, per_tag=10) == generate_variants_dataset(531, per_tag=10)


def test_different_tags_are_all_represented():
    rows = generate_variants_dataset(531, per_tag=3)
    tags = {row["variant_tag"] for row in rows}
    assert len(tags) == 21, tags  # 17개 + 이름 뒤 어미·조사 4개(#614)


@pytest.mark.parametrize("tag_fn_name", sorted(VARIANT_TAGS))
def test_current_core_detects_every_variant_shape(tag_fn_name):
    """#531의 핵심 전제 — 이 세트에 실린 표기는 지금 main이 전부 잡아야 한다(9/28 이후 고친
    것들이므로). 못 잡는 게 있으면 표기를 잘못 만들었거나 core가 되돌아간 것이다."""
    gen = VARIANT_TAGS[tag_fn_name]
    rng = __import__("random").Random(f"test:{tag_fn_name}")
    pipeline = Pipeline()
    for _ in range(30):
        doc = gen(rng)
        gold = {(lb["kind"], lb["start"], lb["end"]) for lb in doc.labels}
        pred = {(d.kind, d.start, d.end) for d in pipeline.scan(doc.text)}
        assert gold & pred, f"{tag_fn_name}: {doc.text!r} 미탐 -> {[(d.kind, d.text) for d in pipeline.scan(doc.text)]}"


def test_committed_variants_v1_dataset_is_reproducible_from_seed():
    """제출 수치 근거인 synth_v1과 같은 원칙 — variants_v1.jsonl도 시드로 다시 만들 수 있어야 한다."""
    expected = _load_rows(_DATASETS / "variants_v1.jsonl")
    assert generate_variants_dataset(531, per_tag=15) == [
        {"text": r["text"], "labels": r["labels"], "difficulty": r["difficulty"], "variant_tag": r["variant_tag"]}
        for r in expected
    ]


def test_cli_writes_a_new_file(tmp_path, monkeypatch):
    target = tmp_path / "variants_small.jsonl"
    monkeypatch.setattr(sys, "argv", ["generate_variants", "--seed", "1", "--per-tag", "2", "--out", str(target)])
    main()
    rows = _load_rows(target)
    assert len(rows) == 2 * len(VARIANT_TAGS)  # 생성 함수 수(24) 기준 — 일부는 같은 variant_tag를 공유한다
    assert rows == generate_variants_dataset(1, per_tag=2)
