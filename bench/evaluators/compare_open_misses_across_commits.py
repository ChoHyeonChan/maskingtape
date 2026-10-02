# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""열린 미탐 세트(#610)를 두 커밋의 core로 각각 재서 비교한다.

쓰임새는 둘이다.
- core PR이 이슈를 고쳤을 때 "고치기 전 → 고친 뒤" 재현율을 한 명령으로 보인다.
- 반대로, 예전에는 잡히던 모양이 언제부터 새는지(회귀) 숫자로 보인다. #600이 그 예다.

동작 원리:
1. 격리된 임시 가상환경에 각 커밋의 core만 설치해 채점하는 부분은
   `compare_variants_across_commits.py`의 `compare()`를 그대로 쓴다(같은 프로세스에서 경로만
   바꾸는 방식이 왜 안 되는지는 그 파일 설명 참고). 채점 스크립트만 `evaluate_open_misses.py`로 바꾼다.
2. 두 결과를 (이슈, 태그)로 맞춰 재현율을 나란히 놓고, 달라진 줄에 표시를 붙인다.

사용법:
    python -m bench.evaluators.compare_open_misses_across_commits \\
        bench/datasets/open_misses_v1.jsonl --before <커밋> --after HEAD
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bench.evaluators.compare_variants_across_commits import compare

_EVALUATE_OPEN_MISSES_SCRIPT = Path(__file__).resolve().with_name("evaluate_open_misses.py")


def _recall_by_tag(result: dict) -> dict[tuple[int, str], float]:
    """evaluate_open_misses.py의 --json 결과를 (이슈, 태그) → 재현율로 바꾼다."""
    return {(row["issue"], row["tag"]): row["recall"] for row in result["per_tag"]}


def format_comparison_table(result: dict, before_label: str, after_label: str) -> str:
    """이슈 번호순으로 태그별 재현율을 나란히 찍는다. 올랐으면 ▲, 내렸으면 ▼를 붙인다."""
    before, after = _recall_by_tag(result["before"]), _recall_by_tag(result["after"])
    lines = [f"{'issue':<7} {'tag':<32} {before_label:>12} {after_label:>12}"]
    for issue, tag in sorted(set(before) | set(after)):
        b, a = before.get((issue, tag), 0.0), after.get((issue, tag), 0.0)
        mark = " ▲" if a > b else " ▼" if a < b else ""
        lines.append(f"#{issue:<6} {tag:<32} {b:>12.3f} {a:>12.3f}{mark}")
    lines.append("")
    lines.append(
        f"정답과 안 겹치는 오탐(fp): {before_label} {result['before']['total_fp']}건 → "
        f"{after_label} {result['after']['total_fp']}건"
    )
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="열린 미탐 세트를 두 커밋의 core로 비교")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--before", required=True, help="비교 기준 커밋")
    parser.add_argument("--after", default="HEAD", help="비교 대상 커밋(기본 HEAD)")
    parser.add_argument("--json", type=Path, default=None, help="원시 결과를 JSON으로도 저장 (선택)")
    args = parser.parse_args()

    result = compare(args.dataset.resolve(), args.before, args.after, _EVALUATE_OPEN_MISSES_SCRIPT)
    print(format_comparison_table(result, args.before, args.after))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
