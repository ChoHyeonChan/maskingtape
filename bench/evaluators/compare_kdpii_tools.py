# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII에서 maskingtape와 다른 오픈소스 PII 도구를 같은 기준으로 채점한다(#457, 발표 자료 타 도구 비교).

지표:
- 다 가림: 우리 11종 정답 span의 글자가 어떤 탐지로든(종류 무관) 전부 덮였나. 유출 관점의 재현율이다.
  숫자가 4개 이상인 정답(번호류)은 숫자만 다 덮이면 가린 것으로 본다. KDPII는 「우리은행 9552-…」처럼
  은행명·지역명까지 span에 넣는데, 그 이름이 보이는 것은 유출이 아니다. 나머지는 공백을 뺀 모든 글자를 본다.
- 엉뚱한 곳 가림: 정답과도, KDPII의 범위 밖 라벨(직장·직위·닉네임 등)과도 전혀 안 겹치는 탐지 수.
- 정답 없는 문장 중 가림: 라벨이 하나도 없는 문장 중 무엇이라도 가린 문장 수.
- overlap·exact: 종류가 같고 구간이 겹치면(overlap) / 똑같으면(exact) 맞음. 도구마다 span을 자르는 관행이
  달라 overlap을 주로 본다. 매핑표에 없는 라벨(pii_tool_adapters.py)은 여기서 빠진다.

KDPII는 보고용 데이터다(bench README #456). 이 결과를 보고 규칙을 고치지 않는다.

사용법(비교용 가상환경, bench README 「KDPII 타 도구 비교」):
    python -m bench.fetch_kdpii --split test
    python -m bench.evaluators.compare_kdpii_tools bench/datasets/external/kdpii_test.jsonl \
        --report bench/datasets/external/kdpii_tools_report.md
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bench.evaluators.evaluate import load_dataset
from bench.evaluators.pii_tool_adapters import BUILDERS, Tool, build_tools

KINDS = (
    "name", "phone", "email", "rrn", "address", "card",
    "biz_reg", "passport", "account", "birth_date", "driver_license",
)  # fmt: skip


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def _prf(matched_pred: int, n_pred: int, matched_gold: int, n_gold: int) -> list[float]:
    p = matched_pred / n_pred if n_pred else 0.0
    r = matched_gold / n_gold if n_gold else 0.0
    return [p, r, 2 * p * r / (p + r) if p + r else 0.0]


def mask_state(text: str, covered: list[bool], span: dict) -> str:
    """정답 span이 다 가려졌나(full), 일부만(partial), 전혀 안 가려졌나(none)."""
    idx = range(span["start"], span["end"])
    digits = [i for i in idx if text[i].isdigit()]
    need = digits if len(digits) >= 4 else [i for i in idx if not text[i].isspace()]
    hit = sum(covered[i] for i in need)
    return "full" if hit == len(need) else ("partial" if hit else "none")


def score(rows: list[dict], preds: list[list[dict]]) -> dict:
    """문장별 예측(어댑터 출력 목록)을 채점한다. 개수와 비율을 함께 돌려준다."""
    if len(rows) != len(preds):
        raise ValueError(f"문장 {len(rows)}개와 예측 {len(preds)}개가 다르다")
    exact = defaultdict(lambda: [0, 0, 0])  # 종류 → [맞음, 예측, 정답]
    overlap = defaultdict(lambda: [0, 0, 0, 0])  # 종류 → [겹친 예측, 예측, 겹친 정답, 정답]
    mask = {"full": 0, "partial": 0, "none": 0}
    mask_kind = defaultdict(lambda: [0, 0])  # 종류 → [다 가림, 정답]
    all_labels = [0, 0]  # 범위 밖 라벨까지 포함한 [다 가림, 라벨]
    stray = n_pred = 0
    neg_docs = [0, 0]  # [정답 없는 문장 중 무엇이라도 가린 문장, 정답 없는 문장]
    for row, found in zip(rows, preds):
        text, gold, other = row["text"], row["labels"], row.get("other", [])
        typed = [p for p in found if p["kind"]]
        n_pred += len(found)

        gset = {(g["kind"], g["start"], g["end"]) for g in gold}
        pset = {(p["kind"], p["start"], p["end"]) for p in typed}
        for k in {g[0] for g in gset} | {p[0] for p in pset}:
            gk = {g for g in gset if g[0] == k}
            pk = {p for p in pset if p[0] == k}
            exact[k][0] += len(gk & pk)
            exact[k][1] += len(pk)
            exact[k][2] += len(gk)
        for k in {g["kind"] for g in gold} | {p["kind"] for p in typed}:
            gk = [g for g in gold if g["kind"] == k]
            pk = [p for p in typed if p["kind"] == k]
            overlap[k][0] += sum(1 for p in pk if any(_overlaps(p, g) for g in gk))
            overlap[k][1] += len(pk)
            overlap[k][2] += sum(1 for g in gk if any(_overlaps(g, p) for p in pk))
            overlap[k][3] += len(gk)

        covered = [False] * len(text)
        for p in found:
            for i in range(p["start"], min(p["end"], len(text))):
                covered[i] = True
        for g in gold:
            state = mask_state(text, covered, g)
            mask[state] += 1
            mask_kind[g["kind"]][1] += 1
            mask_kind[g["kind"]][0] += state == "full"
        for g in gold + other:
            all_labels[1] += 1
            all_labels[0] += mask_state(text, covered, g) == "full"

        every = gold + other
        stray += sum(1 for p in found if not any(_overlaps(p, g) for g in every))
        if not every:
            neg_docs[1] += 1
            neg_docs[0] += bool(found)

    ex = [sum(v[i] for k, v in exact.items() if k in KINDS) for i in range(3)]
    ov = [sum(v[i] for k, v in overlap.items() if k in KINDS) for i in range(4)]
    return {
        "n_gold": sum(mask.values()),
        **mask,
        "mask_kind": {k: v for k, v in mask_kind.items()},
        "all_labels": all_labels,
        "stray": stray,
        "n_pred": n_pred,
        "neg_docs": neg_docs,
        "exact": _prf(ex[0], ex[1], ex[0], ex[2]),
        "overlap": _prf(*ov),
        "overlap_kind": {k: _prf(*v) for k, v in overlap.items() if k in KINDS},
    }


def run_tool(tool: Tool, rows: list[dict]) -> tuple[list[list[dict]], float]:
    """도구로 모든 문장을 돌려 예측과 문장당 밀리초를 돌려준다."""
    t0 = time.perf_counter()
    preds = [tool.predict(row["text"]) for row in rows]
    return preds, 1000 * (time.perf_counter() - t0) / max(len(rows), 1)


def format_report(
    dataset: Path, rows: list[dict], tools: list[Tool], results: dict[str, dict]
) -> str:
    n_gold = next(iter(results.values()))["n_gold"]
    n_other = sum(len(r.get("other", [])) for r in rows)
    versions = sorted({f"{k} {v}" for t in tools for k, v in t.versions.items()})
    lines = [
        "# KDPII 타 도구 비교",
        "",
        f"- 데이터셋: `{dataset.name}` ({len(rows)}문장, 우리 11종 정답 {n_gold}개, 범위 밖 라벨 {n_other}개)",
        f"- 생성 시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- 버전: {' · '.join(versions)}",
        "",
        "| 도구 | 다 가림 | 일부만 | 그대로 노출 | 엉뚱한 곳 가림 | 정답 없는 문장 중 가림 "
        "| overlap P | overlap R | overlap F1 | exact F1 | ms/문장 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for t in tools:
        r = results[t.name]
        (op, orc, of), ef = r["overlap"], r["exact"][2]
        lines.append(
            f"| {t.name} | {r['full']} ({r['full'] / n_gold:.3f}) | {r['partial']} | {r['none']} "
            f"| {r['stray']}/{r['n_pred']} | {r['neg_docs'][0]}/{r['neg_docs'][1]} "
            f"| {op:.3f} | {orc:.3f} | {of:.3f} | {ef:.3f} | {r['ms_per_doc']:.1f} |"
        )
    lines += [
        "",
        "범위 밖 라벨까지 포함한 다 가림 비율: "
        + ", ".join(
            f"{t.name} {results[t.name]['all_labels'][0] / max(results[t.name]['all_labels'][1], 1):.3f}"
            for t in tools
        ),
        "",
        "## 종류별 다 가림 수 · overlap F1",
        "",
        "| 종류 | 정답 | " + " | ".join(t.name for t in tools) + " |",
        "|---|---:|" + "---:|" * len(tools),
    ]
    first = results[tools[0].name]
    for k in KINDS:
        n = first["mask_kind"].get(k, [0, 0])[1]
        if n == 0 and not any(k in results[t.name]["overlap_kind"] for t in tools):
            continue
        cells = [
            f"{results[t.name]['mask_kind'].get(k, [0, 0])[0]} · {results[t.name]['overlap_kind'].get(k, [0, 0, 0])[2]:.3f}"
            for t in tools
        ]
        lines.append(f"| {k} | {n} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="KDPII에서 maskingtape와 다른 오픈소스 PII 도구 비교"
    )
    parser.add_argument("dataset", type=Path, help="bench.fetch_kdpii가 만든 jsonl")
    parser.add_argument(
        "--tools", default=",".join(BUILDERS), help=f"쉼표로 구분(기본: {','.join(BUILDERS)})"
    )
    parser.add_argument("--report", type=Path, help="마크다운 리포트 저장 경로")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    tools = build_tools([t.strip() for t in args.tools.split(",") if t.strip()])
    results = {}
    for tool in tools:
        preds, ms = run_tool(tool, rows)
        results[tool.name] = {**score(rows, preds), "ms_per_doc": ms}
    report = format_report(args.dataset, rows, tools, results)
    print(report)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(f"리포트 저장: {args.report}")


if __name__ == "__main__":
    main()
