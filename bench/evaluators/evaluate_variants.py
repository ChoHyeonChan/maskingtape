# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""표기 변형 평가 세트(#531)를 표기 태그별 재현율로 채점한다.

동작 원리:
1. JSONL의 각 문서(1건당 정답 1개)를 core Pipeline.scan()에 통과시켜 예측 span을 얻는다.
2. 정답과 (kind, start, end) 완전 일치하면 그 태그의 적중으로 센다 — evaluate.py와 같은 기준.
3. 태그별 재현율과 전체 오탐(정답과 안 겹치는 예측) 건수를 낸다.

이 파일은 일부러 `maskingtape`와 표준 라이브러리만 쓰고 `bench.evaluators.evaluate`를
재사용하지 않는다 — #531의 "9/28 대비" 비교(`compare_variants_across_commits.py`)가 이
파일을 옛 커밋의 `maskingtape`만 설치한 임시 가상환경에서 그대로 실행해야 하는데,
`bench` 패키지까지 그 환경에 설치하면 절차가 번거로워진다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from maskingtape.pipeline import Pipeline


@dataclass
class TagCounts:
    tp: int = 0
    fn: int = 0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0


def load_dataset(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def evaluate_variants(rows: list[dict], pipeline: Pipeline) -> tuple[dict[str, TagCounts], int]:
    """태그별 TagCounts와 전체 오탐(fp) 건수를 반환한다."""
    per_tag: dict[str, TagCounts] = {}
    total_fp = 0
    for row in rows:
        gold = {(lb["kind"], lb["start"], lb["end"]) for lb in row["labels"]}
        pred = {(d.kind, d.start, d.end) for d in pipeline.scan(row["text"])}
        tag = row["variant_tag"]
        counts = per_tag.setdefault(tag, TagCounts())
        if gold & pred:
            counts.tp += 1
        else:
            counts.fn += 1
        total_fp += len(pred - gold)
    return per_tag, total_fp


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="표기 변형 평가 세트를 표기 태그별 재현율로 채점")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--json", type=Path, default=None, help="결과를 JSON으로도 저장할 경로 (선택)")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    per_tag, total_fp = evaluate_variants(rows, Pipeline())

    title = "표기 태그별 재현율"
    print(title)
    print("-" * len(title))
    print(f"{'tag':<28} {'recall':>8} {'tp':>4} {'fn':>4}")
    for tag in sorted(per_tag):
        c = per_tag[tag]
        print(f"{tag:<28} {c.recall:>8.3f} {c.tp:>4} {c.fn:>4}")
    print(f"\n전체 오탐(fp): {total_fp}건")

    if args.json:
        payload = {
            "per_tag": {tag: {"tp": c.tp, "fn": c.fn, "recall": c.recall} for tag, c in per_tag.items()},
            "total_fp": total_fp,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
