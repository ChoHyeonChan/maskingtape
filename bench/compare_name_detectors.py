"""이름(name) 탐지 방식 비교 — 규칙판(NameDetector 단독) vs 하이브리드(LLM + 규칙 안전망).

동작 원리:
1. core에 이름을 찾는 방법이 두 가지 있다 — default_detectors()(성씨 사전 기반 규칙판만)와
   llm_detectors()(로컬 LLM이 문맥으로 판단하고, 확신도 0.75 이상 규칙판을 안전망으로 겹치는 하이브리드).
   같은 데이터셋을 두 Pipeline 구성으로 각각 돌려서 "name" kind만 뽑아 precision/recall/F1을 비교한다.
2. LLM 쪽은 로컬 Ollama가 떠 있어야 동작하는데, 없으면 LLMNameDetector가 RuntimeError를 낸다.
   이걸 잡아서 "LLM 사용 불가"로 표시하고 규칙판 결과만 정상 출력한다 — Ollama 없는 환경(CI 등)에서도
   도구 자체는 안 죽는다.
3. 두 방식 다 evaluate.py의 evaluate()를 그대로 재사용해 전체 kind별 점수를 낸 뒤 "name" 행만 뽑는다 —
   채점 로직을 새로 만들지 않고 검증된 기존 코드를 그대로 쓴다.

사용법:
    python -m bench.compare_name_detectors bench/datasets/synth_v1.jsonl
"""

from __future__ import annotations

import argparse
from pathlib import Path

from maskingtape.detectors import default_detectors, llm_detectors
from maskingtape.pipeline import Pipeline

from bench.evaluate import Counts, evaluate, load_dataset


def evaluate_name_only(rows: list[dict], pipeline: Pipeline) -> Counts:
    """전체 kind별 결과에서 "name" 행만 뽑는다 (라벨이 하나도 없으면 0으로 채운 빈 Counts)."""
    results = evaluate(rows, pipeline)
    return results.get("name", Counts())


def try_evaluate_llm_name(rows: list[dict], pipeline: Pipeline) -> Counts | None:
    """LLM 파이프라인을 돌리되, Ollama 연결 실패(RuntimeError)는 예외 대신 None으로 알린다.

    pipeline을 밖에서 주입받는 구조라, 테스트에서는 실제 Ollama 없이도 가짜 탐지기로
    "연결 실패" 상황을 그대로 재현해 검증할 수 있다.
    """
    try:
        return evaluate_name_only(rows, pipeline)
    except RuntimeError as exc:
        print(f"[안내] LLM 탐지기를 사용할 수 없습니다: {exc}")
        return None


def format_comparison(rule_counts: Counts, llm_counts: Counts | None) -> str:
    lines = [
        "이름(name) 탐지 방식 비교",
        "--------------------------",
        f"{'방식':<12} {'precision':>10} {'recall':>10} {'f1':>10} {'tp':>6} {'fp':>6} {'fn':>6}",
        f"{'규칙판':<12} {rule_counts.precision:>10.3f} {rule_counts.recall:>10.3f} "
        f"{rule_counts.f1:>10.3f} {rule_counts.tp:>6} {rule_counts.fp:>6} {rule_counts.fn:>6}",
    ]
    if llm_counts is None:
        lines.append(f"{'하이브리드':<12} {'(LLM 사용 불가 — 로컬 Ollama 실행 후 재시도)':>0}")
    else:
        lines.append(
            f"{'하이브리드':<12} {llm_counts.precision:>10.3f} {llm_counts.recall:>10.3f} "
            f"{llm_counts.f1:>10.3f} {llm_counts.tp:>6} {llm_counts.fp:>6} {llm_counts.fn:>6}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="이름 탐지 방식(규칙판 vs 하이브리드) 정확도 비교")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--model", type=str, default="qwen2.5:7b", help="비교에 쓸 로컬 Ollama 모델")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    rule_counts = evaluate_name_only(rows, Pipeline(detectors=default_detectors()))
    llm_counts = try_evaluate_llm_name(rows, Pipeline(detectors=llm_detectors(args.model)))
    print(format_comparison(rule_counts, llm_counts))


if __name__ == "__main__":
    main()
