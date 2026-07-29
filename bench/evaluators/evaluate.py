"""탐지 결과 vs 정답 라벨 → precision/recall/F1 리포트.

동작 원리:
1. JSONL 데이터셋의 각 문서를 core의 Pipeline.scan()에 통과시켜 예측 span을 얻는다.
2. 예측 span과 정답 span을 (kind, start, end) 완전 일치(exact match) 기준으로 비교한다.
3. kind별 + 난이도별(easy/hard/negative) + 전체(micro) precision/recall/F1을 집계해
   표로 출력하고, --report 옵션이 있으면 마크다운 리포트 파일로도 저장한다.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
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


def _totalize(per_group: dict[str, Counts]) -> dict[str, Counts]:
    total = Counts()
    for c in per_group.values():
        total.tp += c.tp
        total.fp += c.fp
        total.fn += c.fn
    per_group["__overall__"] = total
    return per_group


def evaluate(rows: list[dict], pipeline: Pipeline) -> dict[str, Counts]:
    """개인정보 종류(kind)별로 precision/recall/F1 집계."""
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

    return _totalize(per_kind)


def evaluate_by_difficulty(rows: list[dict], pipeline: Pipeline) -> dict[str, Counts]:
    """난이도(easy/hard/negative)별로 precision/recall/F1 집계.

    difficulty 필드가 없는 구형 데이터셋 행은 "unknown"으로 묶는다 (하위 호환).
    """
    per_difficulty: dict[str, Counts] = {}

    for row in rows:
        difficulty = row.get("difficulty", "unknown")
        gold = gold_spans(row)
        pred = predicted_spans(pipeline, row["text"])
        c = per_difficulty.setdefault(difficulty, Counts())
        c.tp += len(gold & pred)
        c.fp += len(pred - gold)
        c.fn += len(gold - pred)

    return _totalize(per_difficulty)


def _format_table(title: str, results: dict[str, Counts]) -> str:
    results = dict(results)
    overall = results.pop("__overall__")
    lines = [
        title,
        f"{'-' * len(title)}",
        f"{'group':<10} {'precision':>10} {'recall':>10} {'f1':>10} {'tp':>6} {'fp':>6} {'fn':>6}",
    ]
    for group in sorted(results):
        c = results[group]
        lines.append(f"{group:<10} {c.precision:>10.3f} {c.recall:>10.3f} {c.f1:>10.3f} {c.tp:>6} {c.fp:>6} {c.fn:>6}")
    lines.append("-" * 60)
    lines.append(
        f"{'overall':<10} {overall.precision:>10.3f} {overall.recall:>10.3f} "
        f"{overall.f1:>10.3f} {overall.tp:>6} {overall.fp:>6} {overall.fn:>6}"
    )
    results["__overall__"] = overall  # 호출자가 재사용할 수 있도록 원복
    return "\n".join(lines)


def print_report(kind_results: dict[str, Counts], difficulty_results: dict[str, Counts]) -> None:
    print(_format_table("종류(kind)별 결과", kind_results))
    print()
    print(_format_table("난이도(difficulty)별 결과", difficulty_results))


def _markdown_table(results: dict[str, Counts]) -> str:
    results = dict(results)
    overall = results.pop("__overall__")
    lines = ["| group | precision | recall | f1 | tp | fp | fn |", "|---|---|---|---|---|---|---|"]
    for group in sorted(results):
        c = results[group]
        lines.append(f"| {group} | {c.precision:.3f} | {c.recall:.3f} | {c.f1:.3f} | {c.tp} | {c.fp} | {c.fn} |")
    lines.append(
        f"| **overall** | **{overall.precision:.3f}** | **{overall.recall:.3f}** | "
        f"**{overall.f1:.3f}** | {overall.tp} | {overall.fp} | {overall.fn} |"
    )
    return "\n".join(lines)


def write_markdown_report(
    out_path: Path,
    dataset_path: Path,
    doc_count: int,
    kind_results: dict[str, Counts],
    difficulty_results: dict[str, Counts],
) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = f"""# maskingtape 합성 벤치마크 정확도 리포트

- 데이터셋: `{dataset_path}` ({doc_count}건)
- 생성 시각: {generated_at}
- 평가 방식: span 완전 일치(exact match) 기준 precision/recall/F1

## 종류(kind)별 결과

{_markdown_table(kind_results)}

## 난이도(difficulty)별 결과

{_markdown_table(difficulty_results)}

- `easy`: 하이픈 등 표준 구분자를 사용한 명확한 표기
- `hard`: 구분자 없음/국제표기/도로명+아파트 등 상대적으로 탐지가 어려운 표기
- `negative`: 개인정보가 전혀 없는(또는 distractor만 있는) 문서 — 오탐(FP) 측정용

## 참고

- `name`/`address`는 core에 아직 탐지기가 구현되지 않아 recall 0으로 나온다 —
  생성기 버그가 아니라 현재 core 구현 범위를 정확히 반영하는 결과다.
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="합성 데이터셋으로 탐지 정확도(F1) 평가")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--report", type=Path, default=None, help="마크다운 리포트를 저장할 경로 (선택)")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    pipeline = Pipeline()
    kind_results = evaluate(rows, pipeline)
    difficulty_results = evaluate_by_difficulty(rows, pipeline)
    print_report(kind_results, difficulty_results)

    if args.report:
        write_markdown_report(args.report, args.dataset, len(rows), kind_results, difficulty_results)
        print(f"\n리포트 저장 완료: {args.report}")


if __name__ == "__main__":
    main()
