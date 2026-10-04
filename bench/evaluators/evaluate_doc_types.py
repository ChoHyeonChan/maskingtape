# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 이름 평가 세트(#661)를 문서 종류별로 채점한다.

동작 원리:
1. 행을 `doc_type`(판결문·상담 기록·사내 메일·회의록·엑셀 명단)으로 묶는다.
2. 묶음마다 evaluate.py의 `evaluate()`로 종류(kind)별 tp·fp·fn을 세고, 이름 행과 전체 행의
   precision·recall·F1·F2를 뽑는다. 채점 기준은 evaluate.py와 같은 완전 일치다.
3. error_breakdown.py로 이름의 유출 기준 재현율((적중 + 가려짐) / 정답 수)을 함께 낸다 —
   조사 한 글자를 더 가린 것처럼 유출이 아닌 미탐을 구분해 보기 위해서다.

멘토링(2026-10-04)에서 "이름이 개인정보인지는 문서 성격에 따라 달라진다 — 판결문은 이름이 곧
개인정보"라는 의견을 받았다. 문서 종류를 섞은 평균 하나로는 판결문 같은 고위험 문서가 얼마나
약한지 보이지 않아서, 종류별로 나눠 본다.

사용법:
    python -m bench.evaluators.evaluate_doc_types bench/datasets/doc_types_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from maskingtape.pipeline import Pipeline

from bench.evaluators.error_breakdown import breakdown_errors
from bench.evaluators.evaluate import Counts, evaluate, load_dataset

# 표에 찍는 순서 — 이름이 개인정보로서 무거운 문서부터.
DOC_TYPE_ORDER = ("judgment", "counseling", "email", "minutes", "roster")
DOC_TYPE_LABELS = {
    "judgment": "판결문",
    "counseling": "상담 기록",
    "email": "사내 메일",
    "minutes": "회의록",
    "roster": "엑셀 명단",
}


def evaluate_doc_types(rows: list[dict], pipeline: Pipeline) -> dict[str, dict]:
    """문서 종류별 {"name": Counts, "overall": Counts, "name_leak_recall": float, "docs": int}."""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["doc_type"], []).append(row)
    result: dict[str, dict] = {}
    for doc_type, group in groups.items():
        counts = evaluate(group, pipeline)
        breakdown = breakdown_errors(group, pipeline)
        name_breakdown = breakdown.get("name")
        result[doc_type] = {
            "docs": len(group),
            "name": counts.get("name", Counts()),
            "overall": counts["__overall__"],
            "name_leak_recall": name_breakdown.leak_recall if name_breakdown else 0.0,
        }
    return result


def _ordered(result: dict[str, dict]) -> list[str]:
    known = [t for t in DOC_TYPE_ORDER if t in result]
    return known + sorted(t for t in result if t not in DOC_TYPE_ORDER)


def format_report(result: dict[str, dict]) -> str:
    """문서 종류별 이름·전체 지표 표. 이름 열이 이 세트의 주 지표다."""
    header = (
        f"{'doc_type':<12} {'docs':>4} | {'name_P':>6} {'name_R':>6} {'name_F1':>7} {'name_F2':>7} "
        f"{'leak_R':>6} {'tp':>4} {'fp':>4} {'fn':>4} | {'all_F1':>6} {'all_F2':>6}"
    )
    lines = ["문서 성격별 이름 정확도 (완전 일치, leak_R=유출 기준 재현율)", "-" * len(header), header]
    for doc_type in _ordered(result):
        r = result[doc_type]
        n, o = r["name"], r["overall"]
        lines.append(
            f"{doc_type:<12} {r['docs']:>4} | {n.precision:>6.3f} {n.recall:>6.3f} {n.f1:>7.3f} {n.f2:>7.3f} "
            f"{r['name_leak_recall']:>6.3f} {n.tp:>4} {n.fp:>4} {n.fn:>4} | {o.f1:>6.3f} {o.f2:>6.3f}"
        )
    return "\n".join(lines)


def main() -> None:
    # Windows 콘솔 기본 코드페이지(cp949)에서도 깨지지 않게 stdout을 UTF-8로 고정한다(#317).
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="문서 성격별 이름 평가 세트를 문서 종류별로 채점")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--json", type=Path, default=None, help="결과를 JSON으로도 저장할 경로 (선택)")
    args = parser.parse_args()

    result = evaluate_doc_types(load_dataset(args.dataset), Pipeline())
    print(format_report(result))

    if args.json:
        payload = {
            doc_type: {
                "docs": r["docs"],
                "name_leak_recall": r["name_leak_recall"],
                **{
                    f"{group}_{metric}": getattr(r[group], metric)
                    for group in ("name", "overall")
                    for metric in ("precision", "recall", "f1", "f2", "tp", "fp", "fn")
                },
            }
            for doc_type, r in result.items()
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
