# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""학습 전/후 모델 비교표 (#458) — 규칙 전용 · 7B · 1.5B 원본 · 1.5B 학습 모델을 같은 벤치로 잰다.

동작 원리:
1. 정확도는 bench의 기존 채점기를 그대로 쓴다 — compare_name_detectors.evaluate_name_only(완전 일치
   이름 P/R/F1)와 evaluate_attacks(공격 판 재현율). 새 채점 논리를 만들지 않는다.
2. 모델마다 하이브리드(llm_detectors)와 LLM 단독(규칙 안전망 뺀 것) 둘 다 잰다 — 단독 점수가 "모델 자체"의
   실력이고, 하이브리드가 제품 점수다.
3. 속도는 보고용 세트에서 문서당 평균 시간(첫 호출은 로딩이라 빼고 잰다), 크기는 Ollama /api/tags의
   파일 크기다.
4. 모델이 문서 하나에서 실패하면(JSON을 끝맺지 못하고 타임아웃 — 원본 1.5B에서 실제로 났다) 그 문서는
   LLM 결과 없음으로 세고 실패 건수를 표에 적는다. core처럼 예외로 멈추면 비교표를 못 만든다.

사용법 (프로젝트 venv, Ollama 실행 중):
    python -m training.benchmark --models qwen2.5:1.5b maskingtape-name:1.5b qwen2.5:7b --out training/results/compare.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

from maskingtape.detectors import LLMNameDetector, NameDetector, default_detectors, llm_detectors
from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.compare_name_detectors import evaluate_name_only
from bench.evaluators.evaluate import Counts, load_dataset
from bench.evaluators.evaluate_attacks import evaluate_attacks

DATA = Path(__file__).resolve().parent / "data"
DEFAULT_DATASETS = {
    "heldout": DATA / "heldout_v1.jsonl",  # 보고용 템플릿(학습에 안 쓴 것)
    "synth_v1": Path("bench/datasets/synth_v1.jsonl"),  # 제출 수치 근거(템플릿 일부가 학습과 겹침 — 참고용)
}
DEFAULT_ATTACKS = DATA / "heldout_attacks_v1.jsonl"


def model_sizes(host: str = "http://127.0.0.1:11434") -> dict[str, int]:
    with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as resp:  # noqa: S310 — 로컬 Ollama
        return {m["name"]: m["size"] for m in json.load(resp)["models"]}


LLM_TIMEOUT = 45.0  # core 기본 120초 — 벤치에서는 멈추지 않는 모델을 더 빨리 실패로 처리한다


class TolerantLLM(Detector):
    """LLMNameDetector를 감싸 문서 단위 실패(타임아웃·응답 형식 오류)를 빈 결과로 바꾸고 센다."""

    def __init__(self, inner: LLMNameDetector):
        self.inner = inner
        self.failures = 0

    def detect(self, text: str) -> list[Detection]:
        try:
            return self.inner.detect(text)
        except (RuntimeError, TypeError, ValueError):
            self.failures += 1
            return []


def pipelines_for(model: str | None) -> tuple[dict[str, Pipeline], TolerantLLM | None]:
    if model is None:
        return {"hybrid": Pipeline(detectors=default_detectors())}, None
    llm = TolerantLLM(LLMNameDetector(model=model, timeout=LLM_TIMEOUT))
    others = [d for d in llm_detectors(model) if not isinstance(d, LLMNameDetector)]
    rules_only = [d for d in others if not isinstance(d, NameDetector)]
    return {
        "llm_only": Pipeline(detectors=[*rules_only, llm]),
        "hybrid": Pipeline(detectors=[*others, llm]),
    }, llm


def timed_eval(rows: list[dict], pipeline: Pipeline) -> tuple[Counts, float]:
    pipeline.scan(rows[0]["text"])  # 워밍업(모델 로딩)
    start = time.perf_counter()
    counts = evaluate_name_only(rows, pipeline)
    return counts, (time.perf_counter() - start) / len(rows)


def run(models: list[str | None], datasets: dict[str, Path], attacks: Path | None) -> list[dict]:
    sizes = model_sizes() if any(models) else {}
    results = []
    for model in models:
        label = model or "규칙 전용"
        print(f"== {label}", file=sys.stderr)
        pipes, llm = pipelines_for(model)
        entry: dict = {"model": label, "size_mb": round(sizes.get(model, 0) / 1e6) if model else 0, "datasets": {}}
        for ds_name, path in datasets.items():
            rows = load_dataset(path)
            per = {}
            for cfg, pipe in pipes.items():
                before = llm.failures if llm else 0
                counts, sec = timed_eval(rows, pipe)
                per[cfg] = {"p": counts.precision, "r": counts.recall, "f1": counts.f1, "fp": counts.fp,
                            "sec_per_doc": sec, "failures": (llm.failures - before) if llm else 0}
                print(f"   {ds_name}/{cfg}: F1 {counts.f1:.3f} · {sec * 1000:.0f} ms/doc · 실패 {per[cfg]['failures']}", file=sys.stderr)
            entry["datasets"][ds_name] = per
        if attacks is not None and model is not None:
            rows = load_dataset(attacks)
            scores = evaluate_attacks(rows, pipes)
            entry["attacks"] = {
                cfg: {tag: s.attacked_recall for tag, s in tags.items()} for cfg, tags in scores.items()
            }
        results.append(entry)
    return results


def format_markdown(results: list[dict]) -> str:
    lines = ["| 모델 | 크기 | 구성 | " + " | ".join(f"{ds} F1 (P/R, fp, 실패)" for ds in results[0]["datasets"]) + " | 문서당 시간 | 공격 판 재현율(평균) |",
             "|---|---|---|" + "---|" * len(results[0]["datasets"]) + "---|---|"]
    for r in results:
        for cfg in ("llm_only", "hybrid"):
            if cfg not in next(iter(r["datasets"].values())):
                continue
            cells = []
            for ds in r["datasets"].values():
                s = ds[cfg]
                cells.append(f"**{s['f1']:.3f}** ({s['p']:.3f}/{s['r']:.3f}, {s['fp']}, {s.get('failures', 0)})")
            sec = next(iter(r["datasets"].values()))[cfg]["sec_per_doc"]
            att = r.get("attacks", {}).get(cfg)
            att_cell = f"{sum(att.values()) / len(att):.3f}" if att else "—"
            size = f"{r['size_mb']} MB" if r["size_mb"] else "—"
            lines.append(f"| {r['model']} | {size} | {cfg} | " + " | ".join(cells) + f" | {sec * 1000:.0f} ms | {att_cell} |")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="이름 모델 학습 전/후 비교표 (#458)")
    parser.add_argument("--models", nargs="+", default=["qwen2.5:1.5b", "maskingtape-name:1.5b", "qwen2.5:7b"])
    parser.add_argument("--no-rule", action="store_true", help="규칙 전용 행을 빼고 잰다")
    parser.add_argument("--attacks", type=Path, default=DEFAULT_ATTACKS)
    parser.add_argument("--out", type=Path, default=None, help="마크다운 표를 저장할 경로(JSON도 옆에 저장)")
    args = parser.parse_args()

    models: list[str | None] = ([] if args.no_rule else [None]) + list(args.models)
    results = run(models, DEFAULT_DATASETS, args.attacks if args.attacks.exists() else None)
    table = format_markdown(results)
    print(table)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(table + "\n", encoding="utf-8")
        args.out.with_suffix(".json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
