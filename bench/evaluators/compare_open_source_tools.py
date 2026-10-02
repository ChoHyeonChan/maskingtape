# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""오픈소스 PII 도구와 maskingtape를 같은 합성 데이터셋·채점기로 비교한다.

비교 대상은 로컬에서 실행되는 오픈소스 패키지만 허용한다. GPT/Claude 같은 상용 API 모델이나
비상업 전용 라이선스 모델은 이 스크립트에 넣지 않는다. 각 도구가 내보내는 엔티티 이름은
TOOL_KIND_MAPS에서 프로젝트의 kind 이름으로 매핑한 뒤, evaluate.py와 같은 Span/Counts
로직으로 exact match precision/recall/F1/F2를 계산한다.

사용법:
    python -m bench.evaluators.compare_open_source_tools bench/datasets/synth_v1.jsonl \
        --report bench/reports/open_source_baselines_v1.md
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from maskingtape.pipeline import Pipeline

from bench.evaluators.evaluate import (
    Counts,
    Span,
    _markdown_table,
    _totalize,
    gold_spans,
    load_dataset,
)

Predictor = Callable[[str], set[Span]]

SCRUBADUB_KIND_MAP = {
    "credit_card": "card",
    "email": "email",
    "phone": "phone",
}

TOOL_KIND_MAPS = {
    "maskingtape-rules": {
        "account": "account",
        "address": "address",
        "birth_date": "birth_date",
        "biz_reg": "biz_reg",
        "card": "card",
        "driver_license": "driver_license",
        "email": "email",
        "name": "name",
        "passport": "passport",
        "phone": "phone",
        "rrn": "rrn",
    },
    "scrubadub": SCRUBADUB_KIND_MAP,
}


@dataclass(frozen=True)
class ToolRun:
    name: str
    version: str
    license: str
    homepage: str
    kind_map: dict[str, str]
    predict: Predictor


def evaluate_predictor(rows: list[dict], predict: Predictor) -> dict[str, Counts]:
    """evaluate.py와 같은 exact match 기준으로 임의의 예측기를 채점한다."""
    per_kind: dict[str, Counts] = {}

    def counts_for(kind: str) -> Counts:
        return per_kind.setdefault(kind, Counts())

    for row in rows:
        gold = gold_spans(row)
        pred = predict(row["text"])
        all_kinds = {s.kind for s in gold} | {s.kind for s in pred}

        for kind in all_kinds:
            g = {s for s in gold if s.kind == kind}
            p = {s for s in pred if s.kind == kind}
            c = counts_for(kind)
            c.tp += len(g & p)
            c.fp += len(p - g)
            c.fn += len(g - p)

    return _totalize(per_kind)


def _maskingtape_rule_run() -> ToolRun:
    pipeline = Pipeline()

    def predict(text: str) -> set[Span]:
        return {Span(kind=d.kind, start=d.start, end=d.end) for d in pipeline.scan(text)}

    return ToolRun(
        name="maskingtape-rules",
        version=metadata.version("maskingtape"),
        license="Apache-2.0",
        homepage="https://github.com/ChoHyeonChan/maskingtape",
        kind_map=TOOL_KIND_MAPS["maskingtape-rules"],
        predict=predict,
    )


def scrubadub_spans(filths: Iterable[object]) -> set[Span]:
    """scrubadub Filth 객체들을 maskingtape Span 집합으로 변환한다.

    scrubadub에는 한국 주민번호·사업자등록번호·여권번호 같은 kind가 없으므로, 매핑표에 없는
    엔티티 타입은 버린다. "못 잡았다"는 결과는 gold 쪽의 FN으로 그대로 남는다.
    """
    spans = set()
    for filth in filths:
        raw_kind = getattr(filth, "type", None) or getattr(filth, "detector_name", None)
        kind = SCRUBADUB_KIND_MAP.get(str(raw_kind))
        if kind is None:
            continue
        spans.add(Span(kind=kind, start=int(filth.beg), end=int(filth.end)))
    return spans


def _scrubadub_run() -> ToolRun:
    try:
        import scrubadub
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "scrubadub 기준선이 설치되지 않았습니다. "
            '`python -m pip install -e "packages/core[bench-baselines]"` 후 다시 실행하세요.'
        ) from exc

    scrubber = scrubadub.Scrubber()

    def predict(text: str) -> set[Span]:
        return scrubadub_spans(scrubber.iter_filth(text))

    return ToolRun(
        name="scrubadub",
        version=metadata.version("scrubadub"),
        license="MIT metadata / Apache-2.0 classifier",
        homepage="https://github.com/LeapBeyond/scrubadub",
        kind_map=TOOL_KIND_MAPS["scrubadub"],
        predict=predict,
    )


def build_tool_runs(tool_names: list[str]) -> list[ToolRun]:
    builders = {
        "maskingtape-rules": _maskingtape_rule_run,
        "scrubadub": _scrubadub_run,
    }
    unknown = sorted(set(tool_names) - set(builders))
    if unknown:
        raise ValueError(f"알 수 없는 비교 도구: {', '.join(unknown)}")
    return [builders[name]() for name in tool_names]


def _summary_table(results_by_tool: dict[str, dict[str, Counts]]) -> str:
    lines = [
        "| tool | precision | recall | f1 | f2 | tp | fp | fn |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for tool_name, results in results_by_tool.items():
        overall = results["__overall__"]
        lines.append(
            f"| {tool_name} | {overall.precision:.3f} | {overall.recall:.3f} | "
            f"{overall.f1:.3f} | {overall.f2:.3f} | {overall.tp} | {overall.fp} | "
            f"{overall.fn} |"
        )
    return "\n".join(lines)


def _mapping_table(tool_runs: list[ToolRun]) -> str:
    lines = [
        "| tool | raw entity | maskingtape kind |",
        "|---|---|---|",
    ]
    for run in tool_runs:
        for raw_kind, kind in sorted(run.kind_map.items()):
            lines.append(f"| {run.name} | {raw_kind} | {kind} |")
    return "\n".join(lines)


def format_markdown_report(
    dataset_path: Path,
    doc_count: int,
    tool_runs: list[ToolRun],
    results_by_tool: dict[str, dict[str, Counts]],
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dataset_display = Path(dataset_path).as_posix()
    tool_lines = "\n".join(
        f"- {run.name} {run.version}: {run.license}, {run.homepage}" for run in tool_runs
    )
    per_tool_sections = "\n\n".join(
        f"## {run.name} kind별 결과\n\n{_markdown_table(results_by_tool[run.name])}"
        for run in tool_runs
    )
    return f"""# 오픈소스 PII 도구 비교 리포트

- 데이터셋: `{dataset_display}` ({doc_count}건, 합성 데이터)
- 생성 시각: {generated_at}
- 평가 방식: span 완전 일치(exact match) 기준 precision/recall/F1/F2
- 비교 대상: 로컬 실행 오픈소스 도구만 사용. 상용 API 모델·비상업 전용 모델은 제외.

## 비교 도구와 라이선스

{tool_lines}

## 엔티티 매핑

{_mapping_table(tool_runs)}

## 전체 요약

{_summary_table(results_by_tool)}

{per_tool_sections}
"""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="오픈소스 PII 도구와 maskingtape 정확도 비교")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument(
        "--tools",
        default="maskingtape-rules,scrubadub",
        help="쉼표로 구분한 비교 도구 목록 (기본: maskingtape-rules,scrubadub)",
    )
    parser.add_argument("--report", type=Path, default=None, help="마크다운 리포트 저장 경로")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    tool_runs = build_tool_runs([tool.strip() for tool in args.tools.split(",") if tool.strip()])
    results_by_tool = {run.name: evaluate_predictor(rows, run.predict) for run in tool_runs}
    report = format_markdown_report(args.dataset, len(rows), tool_runs, results_by_tool)
    print(report)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        print(f"리포트 저장 완료: {args.report}")


if __name__ == "__main__":
    main()
