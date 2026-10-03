# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""열린 미탐 세트(#610)를 core 이슈별·태그별 재현율로 채점한다.

동작 원리:
1. JSONL의 각 문서를 core Pipeline.scan()에 통과시켜 예측 span을 얻는다.
2. target 라벨(그 이슈가 놓친다고 보고한 자리)마다 셋 중 하나로 나눈다.
   - 적중(tp): 예측과 (kind, start, end)가 완전히 같다 — evaluate.py와 같은 기준.
   - 부분(partial): 완전히 같은 예측은 없지만 겹치는 예측이 있다. 일부만 가려졌거나
     (주소가 번지까지만) 다른 종류로 가려진 경우다.
   - 미탐(miss): 겹치는 예측이 하나도 없다. 원문이 통째로 남는다.
3. 재현율은 적중 / target 전체다. 부분은 적중으로 치지 않는다 — 남은 조각이 곧 유출이다.
4. 오탐(fp)은 어떤 정답 라벨과도 겹치지 않는 예측만 센다. 부분 적중을 오탐으로 또 세지 않는다.

일부러 `maskingtape`와 표준 라이브러리만 쓴다(evaluate_variants.py와 같은 이유) — 다른
커밋의 core만 설치한 임시 가상환경에서도 이 파일 하나로 그대로 돌릴 수 있다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from maskingtape.pipeline import Pipeline


@dataclass
class MissCounts:
    tp: int = 0
    partial: int = 0
    miss: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.partial + self.miss

    @property
    def recall(self) -> float:
        """target이 하나도 없으면 ZeroDivisionError 대신 0.0을 돌려준다."""
        return self.tp / self.total if self.total else 0.0

    def add(self, other: MissCounts) -> None:
        self.tp += other.tp
        self.partial += other.partial
        self.miss += other.miss


def load_dataset(path: Path) -> list[dict]:
    """JSONL을 줄 단위로 읽는다. 빈 줄은 건너뛴다."""
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _overlaps(start: int, end: int, other_start: int, other_end: int) -> bool:
    """두 구간이 한 글자라도 겹치는지."""
    return start < other_end and other_start < end


def evaluate_open_misses(rows: list[dict], pipeline: Pipeline) -> tuple[dict[tuple[int, str], MissCounts], int]:
    """(이슈 번호, 태그)별 MissCounts와 전체 오탐 건수를 돌려준다."""
    per_tag: dict[tuple[int, str], MissCounts] = {}
    total_fp = 0
    for row in rows:
        pred = [(d.kind, d.start, d.end) for d in pipeline.scan(row["text"])]
        counts = per_tag.setdefault((row["issue"], row["miss_tag"]), MissCounts())
        for label in row["labels"]:
            if not label.get("target", True):
                continue  # 지금도 잡히는 자리 — 재현율에 넣으면 시작 수치가 부풀려진다
            if (label["kind"], label["start"], label["end"]) in pred:
                counts.tp += 1
            elif any(_overlaps(label["start"], label["end"], s, e) for _, s, e in pred):
                counts.partial += 1
            else:
                counts.miss += 1
        total_fp += sum(
            1
            for _, s, e in pred
            if not any(_overlaps(s, e, lb["start"], lb["end"]) for lb in row["labels"])
        )
    return per_tag, total_fp


def by_issue(per_tag: dict[tuple[int, str], MissCounts]) -> dict[int, MissCounts]:
    """태그별 집계를 이슈 번호별로 합친다(한 이슈에 태그가 여러 개일 수 있다)."""
    per_issue: dict[int, MissCounts] = {}
    for (issue, _tag), counts in per_tag.items():
        per_issue.setdefault(issue, MissCounts()).add(counts)
    return per_issue


def format_report(per_tag: dict[tuple[int, str], MissCounts], total_fp: int) -> str:
    """콘솔용 표 — 이슈 번호순으로 태그를 찍고, 이슈별 소계와 전체 합계를 붙인다."""
    header = f"{'issue':<7} {'tag':<30} {'recall':>7} {'tp':>4} {'partial':>8} {'miss':>5}"
    lines = ["core 이슈별·태그별 재현율 (target 라벨 기준)", "-" * len(header), header]
    for issue, tag in sorted(per_tag):
        c = per_tag[(issue, tag)]
        lines.append(f"#{issue:<6} {tag:<30} {c.recall:>7.3f} {c.tp:>4} {c.partial:>8} {c.miss:>5}")
    lines.append("-" * len(header))
    overall = MissCounts()
    for issue, c in sorted(by_issue(per_tag).items()):
        overall.add(c)
        lines.append(f"#{issue:<6} {'(이슈 소계)':<30} {c.recall:>7.3f} {c.tp:>4} {c.partial:>8} {c.miss:>5}")
    lines.append("-" * len(header))
    lines.append(
        f"{'전체':<7} {'':<30} {overall.recall:>7.3f} {overall.tp:>4} {overall.partial:>8} {overall.miss:>5}"
    )
    lines.append(f"\n정답과 안 겹치는 오탐(fp): {total_fp}건")
    return "\n".join(lines)


def main() -> None:
    # Windows 콘솔 기본 코드페이지(cp949)에서도 깨지지 않게 stdout을 UTF-8로 고정한다(#317).
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="열린 미탐 세트를 core 이슈별 재현율로 채점")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--json", type=Path, default=None, help="결과를 JSON으로도 저장할 경로 (선택)")
    args = parser.parse_args()

    per_tag, total_fp = evaluate_open_misses(load_dataset(args.dataset), Pipeline())
    print(format_report(per_tag, total_fp))

    if args.json:
        payload = {
            "per_tag": [
                {"issue": issue, "tag": tag, "tp": c.tp, "partial": c.partial, "miss": c.miss, "recall": c.recall}
                for (issue, tag), c in sorted(per_tag.items())
            ],
            "total_fp": total_fp,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
