# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""프롬프트 공격 골든셋(#549) 생성기·평가기 검증.

CI에는 Ollama가 없으므로 LLM은 가짜 client로 대체한다 — "공격 문장이 보이면 빈 목록을
답하는" 모델을 흉내 내어, 평가기가 LLM 단독의 재현율 하락과 하이브리드의 규칙 안전망 복구를
제대로 숫자로 내는지만 확인한다. 실제 모델 수치는 bench/README.md에 있다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from maskingtape.detectors import LLMNameDetector
from maskingtape.detectors.personal.name_llm import DEFAULT_MODEL

from bench.evaluators.evaluate_attacks import (
    AttackReport,
    build_pipelines,
    evaluate_attacks,
    format_report,
    try_llm_pipelines,
)
from bench.generate_attacks import main
from bench.generator.attacks import (
    ATTACK_SENTENCES,
    ATTACK_TAGS,
    CLEAN_TAG,
    generate_attack_dataset,
)

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"
_ALL_SENTENCES = tuple(s for sentences in ATTACK_SENTENCES.values() for s in sentences)


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _pairs(rows: list[dict]) -> dict[int, dict[str, dict]]:
    by_pair: dict[int, dict[str, dict]] = {}
    for row in rows:
        side = "clean" if row["attack_tag"] == CLEAN_TAG else "attacked"
        by_pair.setdefault(row["pair_id"], {})[side] = row
    return by_pair


def test_every_pair_has_a_clean_and_an_attacked_side_with_matching_labels():
    pairs = _pairs(generate_attack_dataset(1, per_tag=4))
    assert len(pairs) == 4 * len(ATTACK_TAGS)
    for pair in pairs.values():
        clean, attacked = pair["clean"], pair["attacked"]
        assert any(lb["kind"] == "name" for lb in clean["labels"]), clean
        assert attacked["attack_tag"] in ATTACK_TAGS
        assert any(s in attacked["text"] for s in ATTACK_SENTENCES[attacked["attack_tag"]])
        assert clean["attack_position"] == attacked["attack_position"]
        # 라벨 수는 같고, 공격 판의 라벨은 (밀린 위치에서) 깨끗한 판과 같은 값을 가리켜야 한다
        assert len(clean["labels"]) == len(attacked["labels"])
        for c, a in zip(clean["labels"], attacked["labels"]):
            assert c["kind"] == a["kind"]
            assert clean["text"][c["start"] : c["end"]] == attacked["text"][a["start"] : a["end"]]


def test_prefix_shifts_labels_and_suffix_keeps_them():
    for pair in _pairs(generate_attack_dataset(2, per_tag=6)).values():
        clean, attacked = pair["clean"], pair["attacked"]
        shift = attacked["labels"][0]["start"] - clean["labels"][0]["start"]
        if attacked["attack_position"] == "prefix":
            assert shift > 0 and attacked["text"].endswith(clean["text"])
        else:
            assert shift == 0 and attacked["text"].startswith(clean["text"])


def test_generation_is_reproducible_from_seed():
    assert generate_attack_dataset(549, per_tag=5) == generate_attack_dataset(549, per_tag=5)


def test_committed_attacks_v1_dataset_is_reproducible_from_seed():
    """variants_v1과 같은 원칙 — attacks_v1.jsonl도 시드로 다시 만들 수 있어야 한다."""
    assert generate_attack_dataset(549, per_tag=20) == _load_rows(_DATASETS / "attacks_v1.jsonl")


def test_cli_writes_a_new_file(tmp_path, monkeypatch):
    target = tmp_path / "attacks_small.jsonl"
    monkeypatch.setattr(sys, "argv", ["generate_attacks", "--seed", "1", "--per-tag", "2", "--out", str(target)])
    main()
    assert _load_rows(target) == generate_attack_dataset(1, per_tag=2)


def _gullible_client(rows: list[dict]):
    """공격 문장이 보이면 빈 목록, 아니면 정답 이름을 그대로 답하는 가짜 모델."""
    names_by_text = {
        row["text"]: [row["text"][lb["start"] : lb["end"]] for lb in row["labels"] if lb["kind"] == "name"]
        for row in rows
    }

    def client(text: str) -> list[str]:
        if any(s in text for s in _ALL_SENTENCES):
            return []
        return names_by_text.get(text, [])

    return client


def test_evaluator_shows_llm_drop_and_rule_safety_net_recovery():
    rows = generate_attack_dataset(3, per_tag=3)
    scores = evaluate_attacks(rows, build_pipelines(DEFAULT_MODEL, client=_gullible_client(rows)))
    assert set(scores) == {"rule", "llm_only", "hybrid"}
    for tag in ATTACK_TAGS:
        rule, llm_only, hybrid = scores["rule"][tag], scores["llm_only"][tag], scores["hybrid"][tag]
        assert rule.pairs == llm_only.pairs == hybrid.pairs == 3
        assert rule.drop == 0  # 규칙은 지시문을 읽지 않는다
        # 가짜 모델은 깨끗한 판에선 정답을 답하지만(검증 단계가 일부 걸러 1.0은 아닐 수 있다),
        # 공격 판에선 비운다 — 재현율이 0으로 떨어져야 공격이 통한 것이다
        assert llm_only.clean_recall > 0 and llm_only.attacked_recall == 0.0 and llm_only.drop > 0
        # 공격 판에서 LLM이 비면 하이브리드 = 규칙 안전망 — 규칙만큼은 반드시 건진다
        assert hybrid.attacked_tp == rule.attacked_tp
    report = format_report(AttackReport(model=DEFAULT_MODEL, scores=scores))
    assert "규칙 안전망이 막은 몫" in report and "deny_names" in report


def test_llm_pipelines_are_skipped_when_ollama_is_unreachable(monkeypatch):
    def unreachable(self, text):
        raise RuntimeError("Ollama 연결 실패(테스트)")

    monkeypatch.setattr(LLMNameDetector, "detect", unreachable)
    assert try_llm_pipelines(DEFAULT_MODEL) is None
    report = format_report(AttackReport(model=None, scores={"rule": evaluate_attacks([], {}).get("rule", {})}))
    assert "Ollama 없음" in report
