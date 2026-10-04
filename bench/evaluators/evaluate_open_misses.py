# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""열린 미탐 세트(#610)를 core 이슈별·태그별 재현율로 채점한다.

동작 원리:
1. JSONL의 각 문서를 core Pipeline.scan()에 통과시켜 예측 span을 얻는다.
2. target 라벨(그 이슈가 놓친다고 보고한 자리)마다 셋 중 하나로 나눈다.
   - 적중(tp): 예측과 (kind, start, end)가 완전히 같다 — evaluate.py와 같은 기준.
   - 가려짐(covered): 완전히 같은 예측은 없지만 정답의 모든 글자를 예측이 덮는다. 경계나
     종류만 다르다(#653) — 원문은 남지 않는다.
   - 부분(partial): 일부 글자만 덮는다(주소가 번지까지만 가려짐). 남은 글자가 원문으로 남는다.
   - 미탐(miss): 겹치는 예측이 하나도 없다. 원문이 통째로 남는다.
3. 재현율은 적중 / target 전체다. 가려짐·부분은 적중으로 치지 않는다. 대신 유출 기준
   재현율((적중 + 가려짐) / target 전체)을 따로 낸다 — core가 종류를 어떻게 정할지 아직
   안 정한 모양(#637·#638의 날짜 + 주민번호 뒷자리)도 "다 가렸는지"는 볼 수 있다.
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
    covered: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.covered + self.partial + self.miss

    @property
    def recall(self) -> float:
        """target이 하나도 없으면 ZeroDivisionError 대신 0.0을 돌려준다."""
        return self.tp / self.total if self.total else 0.0

    @property
    def leak_recall(self) -> float:
        """유출 기준 재현율 — 글자가 전부 가려진 비율((적중 + 가려짐) / target 전체)."""
        return (self.tp + self.covered) / self.total if self.total else 0.0

    def add(self, other: MissCounts) -> None:
        self.tp += other.tp
        self.covered += other.covered
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


def _covered_chars(start: int, end: int, spans: list[tuple[int, int]]) -> int:
    """[start, end) 가운데 예측 구간들이 덮는 글자 수. 둘이 나눠 덮어도 합쳐서 센다."""
    return sum(1 for i in range(start, end) if any(s <= i < e for s, e in spans))


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
                continue
            covered = _covered_chars(label["start"], label["end"], [(s, e) for _, s, e in pred])
            if covered == label["end"] - label["start"]:
                counts.covered += 1
            elif covered:
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
    header = (
        f"{'issue':<7} {'tag':<30} {'recall':>7} {'leak_recall':>12} "
        f"{'tp':>4} {'covered':>8} {'partial':>8} {'miss':>5}"
    )

    def row(issue: str, tag: str, c: MissCounts) -> str:
        return (
            f"{issue:<7} {tag:<30} {c.recall:>7.3f} {c.leak_recall:>12.3f} "
            f"{c.tp:>4} {c.covered:>8} {c.partial:>8} {c.miss:>5}"
        )

    lines = ["core 이슈별·태그별 재현율 (target 라벨 기준)", "-" * len(header), header]
    for issue, tag in sorted(per_tag):
        lines.append(row(f"#{issue}", tag, per_tag[(issue, tag)]))
    lines.append("-" * len(header))
    overall = MissCounts()
    for issue, c in sorted(by_issue(per_tag).items()):
        overall.add(c)
        lines.append(row(f"#{issue}", "(이슈 소계)", c))
    lines.append("-" * len(header))
    lines.append(row("전체", "", overall))
    lines.append(
        "recall=완전 일치 / leak_recall=(완전 일치 + 가려짐) / covered=다 가렸지만 경계·종류가 다름 / "
        "partial=일부만 가림 / miss=하나도 못 가림"
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
                {
                    "issue": issue, "tag": tag, "tp": c.tp, "covered": c.covered, "partial": c.partial,
                    "miss": c.miss, "recall": c.recall, "leak_recall": c.leak_recall,
                }
                for (issue, tag), c in sorted(per_tag.items())
            ],
            "total_fp": total_fp,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
