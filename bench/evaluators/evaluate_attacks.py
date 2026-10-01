# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""프롬프트 공격 골든셋(#549)을 공격 종류별 · 탐지 구성별 이름 재현율로 채점한다.

동작 원리:
1. 세트의 문서는 pair_id로 묶인 쌍이다 — 같은 바탕 문서의 깨끗한 판(attack_tag="none")과
   공격 문장을 붙인 판. 두 판의 이름 정답을 각각 채점해 재현율 차이(= 공격이 깎은 몫)를 낸다.
2. 세 구성을 같은 문서로 돌린다:
   - 규칙 전용(default_detectors): LLM이 없어 지시문의 영향을 받지 않는 대조군
   - LLM 단독(규칙 이름 안전망을 뺀 llm_detectors): 공격이 모델에 미치는 영향 그 자체
   - 하이브리드(llm_detectors): 제품 구성. LLM 단독과의 차이가 **규칙 안전망이 막아 준 몫**
3. 채점은 evaluate.py와 같은 (kind, start, end) 완전 일치 기준이고, 이름(name) 라벨만 센다 —
   공격이 겨누는 것이 LLM 이름 탐지이고, 다른 종류는 규칙만 쓰므로 영향이 없다.

Ollama가 없으면 LLM 구성은 건너뛰고 규칙 전용만 낸다(CI 등). 모든 값은 합성이다.

사용법:
    python -m bench.evaluators.evaluate_attacks bench/datasets/attacks_v1.jsonl [--model qwen2.5:7b] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from maskingtape.detectors import LLMNameDetector, NameDetector, default_detectors, llm_detectors
from maskingtape.detectors.base import Detector
from maskingtape.detectors.personal.name_llm import DEFAULT_MODEL
from maskingtape.pipeline import Pipeline

CLEAN_TAG = "none"
CONFIG_NAMES = ("rule", "llm_only", "hybrid")


@dataclass
class TagScore:
    """한 공격 종류 × 한 구성의 집계. clean은 쌍의 깨끗한 판, attacked는 공격 판이다."""

    pairs: int = 0
    clean_tp: int = 0
    clean_total: int = 0
    attacked_tp: int = 0
    attacked_total: int = 0

    @property
    def clean_recall(self) -> float:
        return self.clean_tp / self.clean_total if self.clean_total else 0.0

    @property
    def attacked_recall(self) -> float:
        return self.attacked_tp / self.attacked_total if self.attacked_total else 0.0

    @property
    def drop(self) -> float:
        """공격이 깎은 재현율(깨끗한 판 − 공격 판). 0이면 공격이 통하지 않았다."""
        return self.clean_recall - self.attacked_recall


@dataclass
class AttackReport:
    model: str | None  # None이면 LLM 구성을 돌리지 못했다
    scores: dict[str, dict[str, TagScore]] = field(default_factory=dict)  # config → tag → score


def load_dataset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_pipelines(model: str, client=None) -> dict[str, Pipeline]:
    """세 구성의 파이프라인. client를 주면 LLM 호출을 가짜로 대체한다(테스트용)."""
    hybrid = llm_detectors(model)
    if client is not None:
        hybrid = [LLMNameDetector(model=model, client=client) if isinstance(d, LLMNameDetector) else d for d in hybrid]
    llm_only: list[Detector] = [d for d in hybrid if not isinstance(d, NameDetector)]
    return {
        "rule": Pipeline(detectors=default_detectors()),
        "llm_only": Pipeline(detectors=llm_only),
        "hybrid": Pipeline(detectors=hybrid),
    }


def _name_hits(pipeline: Pipeline, row: dict) -> tuple[int, int]:
    """(맞힌 이름 라벨 수, 이름 라벨 수) — 완전 일치 기준."""
    gold = {(lb["start"], lb["end"]) for lb in row["labels"] if lb["kind"] == "name"}
    if not gold:
        return 0, 0
    predicted = {(d.start, d.end) for d in pipeline.scan(row["text"]) if d.kind == "name"}
    return len(gold & predicted), len(gold)


def evaluate_attacks(rows: list[dict], pipelines: dict[str, Pipeline]) -> dict[str, dict[str, TagScore]]:
    """config → attack_tag → TagScore. 쌍의 깨끗한 판은 그 쌍의 공격 종류 아래에 집계한다."""
    by_pair: dict[int, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        side = "clean" if row["attack_tag"] == CLEAN_TAG else "attacked"
        by_pair[row["pair_id"]][side] = row

    scores: dict[str, dict[str, TagScore]] = {name: defaultdict(TagScore) for name in pipelines}
    for pair in by_pair.values():
        if "clean" not in pair or "attacked" not in pair:
            continue  # 짝이 안 맞는 행은 채점에서 뺀다(세트가 손상된 경우)
        tag = pair["attacked"]["attack_tag"]
        for name, pipeline in pipelines.items():
            score = scores[name][tag]
            score.pairs += 1
            tp, total = _name_hits(pipeline, pair["clean"])
            score.clean_tp += tp
            score.clean_total += total
            tp, total = _name_hits(pipeline, pair["attacked"])
            score.attacked_tp += tp
            score.attacked_total += total
    return {name: dict(tags) for name, tags in scores.items()}


def try_llm_pipelines(model: str) -> dict[str, Pipeline] | None:
    """Ollama가 없으면(연결 실패) None — 규칙 전용만 돌린다."""
    pipelines = build_pipelines(model)
    try:
        pipelines["llm_only"].scan("확인용 문장: 고객 홍길동님")  # 합성 이름, 연결 확인용
    except RuntimeError as exc:
        print(f"[안내] LLM 구성을 건너뜁니다: {exc}", file=sys.stderr)
        return None
    return pipelines


def format_report(report: AttackReport) -> str:
    configs = [c for c in CONFIG_NAMES if c in report.scores]
    tags = sorted({tag for per_config in report.scores.values() for tag in per_config})
    header = ["공격 종류", "쌍"] + [f"{c} 깨끗/공격" for c in configs]
    lines = [" | ".join(header), " | ".join("---" for _ in header)]
    for tag in tags:
        cells = [tag, str(next(iter(report.scores.values()))[tag].pairs)]
        for c in configs:
            s = report.scores[c][tag]
            cells.append(f"{s.clean_recall:.3f} / {s.attacked_recall:.3f}")
        lines.append(" | ".join(cells))
    if "llm_only" in report.scores and "hybrid" in report.scores:
        lines.append("")
        lines.append("규칙 안전망이 막은 몫(하이브리드 − LLM 단독, 공격 판 재현율):")
        for tag in tags:
            gained = report.scores["hybrid"][tag].attacked_recall - report.scores["llm_only"][tag].attacked_recall
            lines.append(f"  {tag}: +{gained:.3f}")
    model_note = report.model if report.model else "(LLM 구성 건너뜀 — Ollama 없음)"
    return f"프롬프트 공격 골든셋 — 이름 재현율 (모델: {model_note})\n\n" + "\n".join(lines)


def to_json(report: AttackReport) -> dict:
    return {
        "model": report.model,
        "scores": {
            config: {
                tag: {
                    "pairs": s.pairs,
                    "clean_recall": round(s.clean_recall, 4),
                    "attacked_recall": round(s.attacked_recall, 4),
                    "drop": round(s.drop, 4),
                }
                for tag, s in tags.items()
            }
            for config, tags in report.scores.items()
        },
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="프롬프트 공격 골든셋(#549)을 공격 종류별 이름 재현율로 채점")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="하이브리드에 쓸 로컬 Ollama 모델")
    parser.add_argument("--json", type=Path, default=None, help="결과를 JSON으로도 저장할 경로 (선택)")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    pipelines = try_llm_pipelines(args.model)
    if pipelines is None:
        pipelines = {"rule": Pipeline(detectors=default_detectors())}
    report = AttackReport(model=args.model if "hybrid" in pipelines else None)
    report.scores = evaluate_attacks(rows, pipelines)
    print(format_report(report))
    if args.json:
        args.json.write_text(json.dumps(to_json(report), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 저장: {args.json}")


if __name__ == "__main__":
    main()
