# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""규칙 전용과 로컬 하이브리드를 여러 데이터셋에서 한 표로 비교한다(#548 종합 비교표).

동작 원리:
1. 데이터셋마다, 모드마다(규칙 전용 = `default_detectors()`, 하이브리드 = `llm_detectors(model)`)
   파이프라인을 만든다.
2. 문서마다 `scan()`을 **한 번만** 부르고 결과를 캐시한다. evaluate.py의 `evaluate()`와
   error_breakdown.py의 `breakdown_errors()`가 같은 문서를 각자 다시 스캔하면 하이브리드는 LLM을
   두 번 부르게 되는데, 문서당 1초가 넘게 걸려 그 비용이 크다.
3. 이름 행과 전체 행의 precision·recall·F1·F2, 이름의 유출 기준 재현율, 문서당 시간을 낸다.
   채점은 evaluate.py와 같은 완전 일치다.

**학습한 이름 모델을 읽을 때 주의**: 기본 모델 `maskingtape-name-1.5b`는 bench 생성기 템플릿
(`documents.py`)으로 만든 데이터로 학습했다(training/). synth_v1·v2는 학습 분포 안쪽이라 하이브리드
수치가 부풀려진다. 바깥 평가에 가까운 건 학습 뒤에 새로 쓴 템플릿인 문서 성격별 세트(#661)다.

사용법:
    python -m bench.evaluators.compare_modes bench/datasets/synth_v1.jsonl bench/datasets/variants_v1.jsonl
    python -m bench.evaluators.compare_modes bench/datasets/doc_types_v1.jsonl --modes hybrid --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from maskingtape.detectors import DEFAULT_MODEL, default_detectors, llm_detectors
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.error_breakdown import breakdown_errors
from bench.evaluators.evaluate import Counts, evaluate, load_dataset

MODES = ("rule", "hybrid")


class CachedPipeline:
    """같은 글을 다시 스캔하면 처음 결과를 돌려주는 얇은 감싸개. `scan()`만 흉내 낸다."""

    def __init__(self, pipeline: Pipeline) -> None:
        self._pipeline = pipeline
        self._cache: dict[str, list[Detection]] = {}
        self.scans = 0  # 실제로 core를 부른 횟수 — 테스트와 시간 계산에 쓴다

    def scan(self, text: str) -> list[Detection]:
        if text not in self._cache:
            self.scans += 1
            self._cache[text] = self._pipeline.scan(text)
        return self._cache[text]


@dataclass
class ModeResult:
    name: Counts
    overall: Counts
    name_leak_recall: float
    seconds_per_doc: float


def run_mode(rows: list[dict], pipeline: Pipeline) -> ModeResult:
    """한 데이터셋을 한 모드로 채점한다. 문서마다 core를 한 번만 부른다."""
    cached = CachedPipeline(pipeline)
    started = time.perf_counter()
    for row in rows:
        cached.scan(row["text"])  # 시간은 스캔에만 든다 — 채점은 캐시를 읽는다
    elapsed = time.perf_counter() - started
    counts = evaluate(rows, cached)
    breakdown = breakdown_errors(rows, cached).get("name")
    return ModeResult(
        name=counts.get("name", Counts()),
        overall=counts["__overall__"],
        name_leak_recall=breakdown.leak_recall if breakdown else 0.0,
        seconds_per_doc=elapsed / len(rows) if rows else 0.0,
    )


def build_pipeline(mode: str, model: str) -> Pipeline:
    if mode == "rule":
        return Pipeline(detectors=default_detectors())
    if mode == "hybrid":
        return Pipeline(detectors=llm_detectors(model))
    raise ValueError(f"모르는 모드: {mode}")


def format_report(results: dict[str, dict[str, ModeResult]], model: str) -> str:
    header = (
        f"{'dataset':<14} {'mode':<7} | {'name_P':>6} {'name_R':>6} {'name_F1':>7} {'name_F2':>7} {'leak_R':>6} "
        f"{'fp':>4} {'fn':>4} | {'all_F1':>6} {'all_F2':>6} | {'s/doc':>6}"
    )
    lines = [f"규칙 전용 vs 로컬 하이브리드 (하이브리드 모델: {model}, 완전 일치)", "-" * len(header), header]
    for dataset, by_mode in results.items():
        for mode, r in by_mode.items():
            n, o = r.name, r.overall
            lines.append(
                f"{dataset:<14} {mode:<7} | {n.precision:>6.3f} {n.recall:>6.3f} {n.f1:>7.3f} {n.f2:>7.3f} "
                f"{r.name_leak_recall:>6.3f} {n.fp:>4} {n.fn:>4} | {o.f1:>6.3f} {o.f2:>6.3f} | {r.seconds_per_doc:>6.2f}"
            )
    return "\n".join(lines)


def main() -> None:
    # Windows 콘솔 기본 코드페이지(cp949)에서도 깨지지 않게 stdout을 UTF-8로 고정한다(#317).
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="규칙 전용 vs 로컬 하이브리드 종합 비교")
    parser.add_argument("datasets", type=Path, nargs="+", help="평가할 JSONL 데이터셋들")
    parser.add_argument("--modes", default="rule,hybrid", help="쉼표로 나눈 모드(rule, hybrid)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="하이브리드에 쓸 로컬 Ollama 모델")
    parser.add_argument("--json", type=Path, default=None, help="결과를 JSON으로도 저장할 경로 (선택)")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    results: dict[str, dict[str, ModeResult]] = {}
    for path in args.datasets:
        rows = load_dataset(path)
        results[path.stem] = {mode: run_mode(rows, build_pipeline(mode, args.model)) for mode in modes}
    print(format_report(results, args.model))

    if args.json:
        payload = {
            "model": args.model,
            "results": {
                dataset: {
                    mode: {
                        **{f"name_{m}": getattr(r.name, m) for m in ("precision", "recall", "f1", "f2", "tp", "fp", "fn")},
                        **{f"overall_{m}": getattr(r.overall, m) for m in ("precision", "recall", "f1", "f2")},
                        "name_leak_recall": r.name_leak_recall,
                        "seconds_per_doc": r.seconds_per_doc,
                    }
                    for mode, r in by_mode.items()
                }
                for dataset, by_mode in results.items()
            },
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
