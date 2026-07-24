"""탐지 신뢰도(confidence) 임계값별로 precision/recall/F1이 어떻게 변하는지 분석한다.

동작 원리:
1. core의 각 Detection에는 confidence(0.0~1.0)가 붙어있지만, 지금까지는 전혀 안 쓰이고 있었다.
2. 후보 임계값마다 confidence가 그 값 미만인 예측을 버린 뒤, evaluate.py와 같은 방식으로
   정답과 비교해 precision/recall/F1을 다시 계산한다.
3. 임계값을 올릴수록 보통 precision은 오르고 recall은 내려가는 트레이드오프가 표로 드러나,
   "오탐을 줄이려면 confidence를 얼마로 잡아야 하는지" 같은 실전 튜닝 근거를 제공한다.

사용법:
    python -m bench.confidence_analysis bench/datasets/synth_v1.jsonl
"""

from __future__ import annotations

import argparse
from pathlib import Path

from maskingtape.pipeline import Pipeline

from bench.evaluate import Counts, Span, gold_spans, load_dataset

DEFAULT_THRESHOLDS = (0.0, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0)


def evaluate_at_threshold(rows: list[dict], pipeline: Pipeline, threshold: float) -> Counts:
    """confidence >= threshold인 예측만 남기고 채점한다."""
    c = Counts()
    for row in rows:
        gold = gold_spans(row)
        pred = {
            Span(kind=d.kind, start=d.start, end=d.end)
            for d in pipeline.scan(row["text"])
            if d.confidence >= threshold
        }
        c.tp += len(gold & pred)
        c.fp += len(pred - gold)
        c.fn += len(gold - pred)
    return c


def evaluate_by_threshold(
    rows: list[dict], pipeline: Pipeline, thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS
) -> dict[float, Counts]:
    return {t: evaluate_at_threshold(rows, pipeline, t) for t in thresholds}


def format_threshold_report(results: dict[float, Counts]) -> str:
    lines = [
        "신뢰도(confidence) 임계값별 결과",
        "--------------------------------",
        f"{'threshold':>9} {'precision':>10} {'recall':>10} {'f1':>10} {'tp':>6} {'fp':>6} {'fn':>6}",
    ]
    for threshold in sorted(results):
        c = results[threshold]
        lines.append(
            f"{threshold:>9.2f} {c.precision:>10.3f} {c.recall:>10.3f} {c.f1:>10.3f} "
            f"{c.tp:>6} {c.fp:>6} {c.fn:>6}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="confidence 임계값별 정확도(F1) 변화 분석")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument(
        "--thresholds",
        type=str,
        default=None,
        help="쉼표로 구분한 임계값 목록 (예: 0.5,0.8,0.95). 생략 시 기본값 사용",
    )
    args = parser.parse_args()

    thresholds = DEFAULT_THRESHOLDS
    if args.thresholds:
        thresholds = tuple(float(t) for t in args.thresholds.split(","))

    rows = load_dataset(args.dataset)
    pipeline = Pipeline()
    results = evaluate_by_threshold(rows, pipeline, thresholds)
    print(format_threshold_report(results))


if __name__ == "__main__":
    main()
