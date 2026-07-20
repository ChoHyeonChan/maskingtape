"""탐지 결과 vs 정답 라벨 → precision/recall/F1 리포트.

동작 원리:
1. JSONL 데이터셋의 각 문서를 core의 Pipeline.scan()에 통과시켜 예측 span을 얻는다.
2. 예측 span과 정답 span을 (kind, start, end) 완전 일치(exact match) 기준으로 비교한다.
3. kind별 + 전체(micro) precision/recall/F1을 집계해 표로 출력한다.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from maskingtape.pipeline import Pipeline


@dataclass(frozen=True)
class Span:
    kind: str
    start: int
    end: int


def load_dataset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def gold_spans(row: dict) -> set[Span]:
    return {Span(kind=lb["kind"], start=lb["start"], end=lb["end"]) for lb in row["labels"]}


def predicted_spans(pipeline: Pipeline, text: str) -> set[Span]:
    return {Span(kind=d.kind, start=d.start, end=d.end) for d in pipeline.scan(text)}


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def evaluate(rows: list[dict], pipeline: Pipeline) -> dict[str, Counts]:
    per_kind: dict[str, Counts] = {}

    def counts_for(kind: str) -> Counts:
        return per_kind.setdefault(kind, Counts())

    for row in rows:
        gold = gold_spans(row)
        pred = predicted_spans(pipeline, row["text"])
        all_kinds = {s.kind for s in gold} | {s.kind for s in pred}

        for kind in all_kinds:
            g = {s for s in gold if s.kind == kind}
            p = {s for s in pred if s.kind == kind}
            c = counts_for(kind)
            c.tp += len(g & p)
            c.fp += len(p - g)
            c.fn += len(g - p)

    total = Counts()
    for c in per_kind.values():
        total.tp += c.tp
        total.fp += c.fp
        total.fn += c.fn
    per_kind["__overall__"] = total
    return per_kind


def print_report(results: dict[str, Counts]) -> None:
    overall = results.pop("__overall__")
    print(f"{'kind':<10} {'precision':>10} {'recall':>10} {'f1':>10} {'tp':>6} {'fp':>6} {'fn':>6}")
    for kind in sorted(results):
        c = results[kind]
        print(f"{kind:<10} {c.precision:>10.3f} {c.recall:>10.3f} {c.f1:>10.3f} {c.tp:>6} {c.fp:>6} {c.fn:>6}")
    print("-" * 60)
    print(
        f"{'overall':<10} {overall.precision:>10.3f} {overall.recall:>10.3f} "
        f"{overall.f1:>10.3f} {overall.tp:>6} {overall.fp:>6} {overall.fn:>6}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="합성 데이터셋으로 탐지 정확도(F1) 평가")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    pipeline = Pipeline()
    results = evaluate(rows, pipeline)
    print_report(results)


if __name__ == "__main__":
    main()
