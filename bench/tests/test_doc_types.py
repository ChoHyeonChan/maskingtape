# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 이름 평가 세트(#661)의 생성기와 평가기 검증.

core가 이 세트에서 얼마나 잡는지는 테스트로 고정하지 않는다 — core가 미탐을 고칠 때마다
bench 테스트가 깨지면 안 된다. 생성기가 약속한 것(라벨 위치, 받침에 맞는 조사, 재현성)과
평가기의 집계만 본다.
"""

from __future__ import annotations

import json
import random
import re
import sys
from itertools import pairwise
from pathlib import Path

import pytest
from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.evaluate_doc_types import evaluate_doc_types, format_report
from bench.generate_doc_types import V1_DATASET_NAME, V1_PER_TYPE, V1_SEED, main
from bench.generator.doc_types import DOC_TYPES, _has_batchim, _josa, generate_doc_types_dataset

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"
_ALL_GENERATORS = [g for gens in DOC_TYPES.values() for g in gens]
_HANGUL_NAME_RE = re.compile(r"[가-힣]{2,4}")


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.mark.parametrize("gen", _ALL_GENERATORS, ids=lambda g: g.__name__)
def test_labels_point_at_clean_values(gen):
    """라벨은 문서 안의 비어 있지 않은 값을 가리키고, 이름 라벨은 한글 2~4자다."""
    rng = random.Random(f"test:{gen.__name__}")
    for _ in range(30):
        doc = gen(rng)
        assert any(lb["kind"] == "name" for lb in doc.labels)
        for lb in doc.labels:
            value = doc.text[lb["start"] : lb["end"]]
            assert value and value == value.strip(), (lb, doc.text)
            if lb["kind"] == "name":
                assert _HANGUL_NAME_RE.fullmatch(value), value


@pytest.mark.parametrize("gen", _ALL_GENERATORS, ids=lambda g: g.__name__)
def test_labels_do_not_overlap(gen):
    rng = random.Random(f"overlap:{gen.__name__}")
    for _ in range(30):
        spans = sorted((lb["start"], lb["end"]) for lb in gen(rng).labels)
        assert all(a_end <= b_start for (_, a_end), (b_start, _) in pairwise(spans))


def test_josa_follows_batchim():
    assert _has_batchim("민") and not _has_batchim("수")
    assert _josa("송준경", "은", "는") == "은"
    assert _josa("김민수", "은", "는") == "는"
    assert _josa("황은민", "과", "와") == "과"


def test_name_after_josa_is_grammatical_in_dataset():
    """'원고 ○○○은/는'·'피고 ○○○과/와'처럼 이름 바로 뒤 조사가 받침과 맞아야 한다(synth_v1의 비문 문제를 되풀이하지 않는다)."""
    pairs = {"은": True, "는": False, "과": True, "와": False, "이": True, "가": False}
    for row in generate_doc_types_dataset(V1_SEED, per_type=10):
        for lb in row["labels"]:
            if lb["kind"] != "name":
                continue
            after = row["text"][lb["end"] : lb["end"] + 2]
            if len(after) == 2 and after[0] in pairs and after[1] == " ":
                name = row["text"][lb["start"] : lb["end"]]
                assert _has_batchim(name[-1]) == pairs[after[0]], (name, after)


def test_every_doc_type_is_represented():
    rows = generate_doc_types_dataset(V1_SEED, per_type=4)
    assert {row["doc_type"] for row in rows} == set(DOC_TYPES)
    assert all(row["difficulty"] == "doc" for row in rows)


def test_committed_dataset_is_reproducible_from_seed():
    assert _load_rows(_DATASETS / V1_DATASET_NAME) == generate_doc_types_dataset(V1_SEED, per_type=V1_PER_TYPE)


def test_cli_writes_a_new_file(tmp_path, monkeypatch):
    target = tmp_path / "doc_types_small.jsonl"
    monkeypatch.setattr(sys, "argv", ["generate_doc_types", "--seed", "1", "--per-type", "2", "--out", str(target)])
    main()
    assert _load_rows(target) == generate_doc_types_dataset(1, per_type=2)


class _FixedDetector(Detector):
    """정해 둔 구간만 돌려주는 가짜 탐지기 — 집계가 core 탐지 결과에 기대지 않게 한다."""

    kind = "fixed"

    def __init__(self, spans: dict[str, list[tuple[str, int, int]]]) -> None:
        self.spans = spans

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(kind=k, start=s, end=e, text=text[s:e], confidence=1.0, detector="fixed")
            for k, s, e in self.spans.get(text, [])
        ]


def test_evaluate_doc_types_groups_by_type_and_reports_name_and_leak_recall():
    judgment = "원고 송준경은 피고 황은민과"
    roster = "이름\n김민수"
    rows = [
        {"text": judgment, "labels": [{"kind": "name", "start": 3, "end": 6}, {"kind": "name", "start": 11, "end": 14}],
         "doc_type": "judgment"},
        {"text": roster, "labels": [{"kind": "name", "start": 3, "end": 6}], "doc_type": "roster"},
    ]
    # 판결문: 하나는 맞히고 하나는 조사까지 한 글자 더 가림(가려짐), 명단: 맞힘
    fixed = _FixedDetector({judgment: [("name", 3, 6), ("name", 11, 15)], roster: [("name", 3, 6)]})
    result = evaluate_doc_types(rows, Pipeline(detectors=[fixed]))
    j = result["judgment"]
    assert (j["name"].tp, j["name"].fp, j["name"].fn) == (1, 1, 1)
    assert j["name_leak_recall"] == 1.0
    assert result["roster"]["name"].recall == 1.0
    report = format_report(result)
    assert report.index("judgment") < report.index("roster")  # 무거운 문서부터 찍는다
