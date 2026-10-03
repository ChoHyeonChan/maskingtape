# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""탐지 결과 vs 정답 라벨 → precision/recall/F1/F2 리포트.

동작 원리:
1. JSONL 데이터셋의 각 문서를 core의 Pipeline.scan()에 통과시켜 예측 span을 얻는다.
2. 예측 span과 정답 span을 (kind, start, end) 완전 일치(exact match) 기준으로 비교한다.
3. kind별 + 난이도별(easy/hard/negative) + 전체(micro) precision/recall/F1/F2를 집계해
   표로 출력하고, --report 옵션이 있으면 마크다운 리포트 파일로도 저장한다.

F2(재현율에 F1보다 더 큰 가중치를 두는 Fβ, β=2)를 F1과 나란히 보는 이유: PII 탐지는
놓친 개인정보(미탐, FN)가 과잉마스킹(오탐, FP)보다 실질적으로 더 위험하다는 게 이 도메인의
평가 관행이다(Microsoft Presidio 평가 프레임워크가 이 이유로 β=2를 권장). F1만 보면 이
비대칭을 놓칠 수 있어 F2를 함께 리포트한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from maskingtape.pipeline import Pipeline

from bench.evaluators.error_breakdown import (
    ErrorBreakdown,
    breakdown_errors,
    format_breakdown_table,
    markdown_breakdown_table,
)


@dataclass(frozen=True)
class Span:
    kind: str
    start: int
    end: int


def load_dataset(path: Path) -> list[dict]:
    """JSONL을 줄 단위로 읽는다 — 파일 끝 개행 등으로 생기는 빈 줄은 조용히 건너뛴다."""
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def gold_spans(row: dict) -> set[Span]:
    """정답 라벨을 Span 집합으로 바꾼다 — 집합이라 순서와 무관하게 교집합/차집합으로 tp/fp/fn을 셀 수 있다."""
    return {Span(kind=lb["kind"], start=lb["start"], end=lb["end"]) for lb in row["labels"]}


def predicted_spans(pipeline: Pipeline, text: str) -> set[Span]:
    """core의 탐지 결과를 gold_spans와 같은 Span 집합 형태로 맞춰, 곧바로 집합 연산으로 비교할 수 있게 한다."""
    return {Span(kind=d.kind, start=d.start, end=d.end) for d in pipeline.scan(text)}


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        """탐지가 하나도 없으면(tp+fp=0) ZeroDivisionError 대신 0.0 — negative 난이도 등에서 발생(#498)."""
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        """정답이 하나도 없으면(tp+fn=0) 0.0 — "탐지 실패"가 아니라 "계산이 성립하지 않음"을 뜻한다(#498)."""
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        """fbeta(1.0)의 별칭 — precision과 recall을 동일 가중치로 조합."""
        return self.fbeta(1.0)

    @property
    def f2(self) -> float:
        """fbeta(2.0)의 별칭 — PII 탐지는 미탐이 오탐보다 위험하다는 도메인 관행대로 recall에
        F1보다 더 큰 가중치를 준다(근거는 모듈 docstring 참고)."""
        return self.fbeta(2.0)

    def fbeta(self, beta: float) -> float:
        """Fβ 스코어. precision·recall이 둘 다 0이면(분모 0) 예외 대신 0.0을 반환한다."""
        p, r = self.precision, self.recall
        beta2 = beta * beta
        return (1 + beta2) * p * r / (beta2 * p + r) if (p + r) else 0.0


def _totalize(per_group: dict[str, Counts]) -> dict[str, Counts]:
    """그룹별 Counts를 합산해 `__overall__` 키로 끼워 넣는다 — 전체(micro) 지표를 그룹별 지표와
    같은 딕셔너리 하나로 들고 다니기 위한 것으로, 호출자가 반복문 하나로 표를 그릴 수 있게 한다."""
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
        """kind가 처음 나오면 빈 Counts를 만들고, 이후로는 같은 인스턴스를 재사용한다(defaultdict 대용)."""
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
    """콘솔 출력용 고정폭 표 — `__overall__`을 먼저 빼서 그룹들을 이름순으로 정렬해 찍고,
    맨 아래에 overall 합계 줄을 따로 고정한다(정렬에 섞이면 항상 맨 위/아래로 튀어 찾기 어렵다)."""
    results = dict(results)
    overall = results.pop("__overall__")
    lines = [
        title,
        f"{'-' * len(title)}",
        f"{'group':<10} {'precision':>10} {'recall':>10} {'f1':>10} {'f2':>10} {'tp':>6} {'fp':>6} {'fn':>6}",
    ]
    for group in sorted(results):
        c = results[group]
        lines.append(
            f"{group:<10} {c.precision:>10.3f} {c.recall:>10.3f} {c.f1:>10.3f} {c.f2:>10.3f} "
            f"{c.tp:>6} {c.fp:>6} {c.fn:>6}"
        )
    lines.append("-" * 70)
    lines.append(
        f"{'overall':<10} {overall.precision:>10.3f} {overall.recall:>10.3f} "
        f"{overall.f1:>10.3f} {overall.f2:>10.3f} {overall.tp:>6} {overall.fp:>6} {overall.fn:>6}"
    )
    results["__overall__"] = overall  # 호출자가 재사용할 수 있도록 원복
    return "\n".join(lines)


def print_report(kind_results: dict[str, Counts], difficulty_results: dict[str, Counts]) -> None:
    """kind별 표와 difficulty별 표를 이 순서로 출력한다 — kind가 "무엇을 놓쳤는지", difficulty가
    "어떤 표기 난이도에서 놓쳤는지"를 보여줘서 둘을 나란히 봐야 원인 진단이 된다."""
    print(_format_table("종류(kind)별 결과", kind_results))
    print()
    print(_format_table("난이도(difficulty)별 결과", difficulty_results))


def _markdown_table(results: dict[str, Counts]) -> str:
    """_format_table과 같은 데이터를 마크다운 표 문법으로 바꾼다 — 결과보고서(`reports/`)에
    그대로 붙여넣거나 GitHub에서 바로 렌더링되도록 콘솔용과 별도로 만든다."""
    results = dict(results)
    overall = results.pop("__overall__")
    lines = ["| group | precision | recall | f1 | f2 | tp | fp | fn |", "|---|---|---|---|---|---|---|---|"]
    for group in sorted(results):
        c = results[group]
        lines.append(
            f"| {group} | {c.precision:.3f} | {c.recall:.3f} | {c.f1:.3f} | {c.f2:.3f} | "
            f"{c.tp} | {c.fp} | {c.fn} |"
        )
    lines.append(
        f"| **overall** | **{overall.precision:.3f}** | **{overall.recall:.3f}** | "
        f"**{overall.f1:.3f}** | **{overall.f2:.3f}** | {overall.tp} | {overall.fp} | {overall.fn} |"
    )
    return "\n".join(lines)


def _markdown_breakdown_section(breakdown: dict[str, ErrorBreakdown] | None) -> str:
    """미탐·오탐 분해(#612) 절. breakdown을 안 넘기면 빈 문자열이라 예전 리포트와 같은 모양이 된다."""
    if breakdown is None:
        return ""
    return f"""
## 미탐·오탐 분해 (유출 기준)

{markdown_breakdown_table(breakdown)}

- 위 표들의 미탐(fn)·오탐(fp)을 "개인정보가 실제로 남았는가"로 다시 나눈 것이다. 수치는 바뀌지 않는다.
- `가려짐`: 정답의 모든 글자를 예측이 덮었다(경계나 종류만 다름) — 유출 없음.
  `부분 유출`: 일부 글자만 덮었다. `완전 유출`: 겹치는 예측이 없다.
- `경계 불일치`: 정답과 겹치는 오탐. `엉뚱한 곳`: 어떤 정답과도 겹치지 않는 오탐.
- `유출 기준 재현율` = (적중 + 가려짐) / 정답 수.
"""


def write_markdown_report(
    out_path: Path,
    dataset_path: Path,
    doc_count: int,
    kind_results: dict[str, Counts],
    difficulty_results: dict[str, Counts],
    breakdown: dict[str, ErrorBreakdown] | None = None,
) -> None:
    """결과보고서 첨부·회의 공유용 마크다운 파일을 만든다 — 생성 시각·데이터셋 경로를 같이
    박아둬서, 나중에 수치만 보고도 "이게 언제 뭘로 잰 결과인지" 재현 조건을 알 수 있게 한다.
    breakdown을 넘기면 미탐·오탐 분해 절(#612)을 맨 끝에 붙인다."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = f"""# maskingtape 합성 벤치마크 정확도 리포트

- 데이터셋: `{dataset_path}` ({doc_count}건)
- 생성 시각: {generated_at}
- 평가 방식: span 완전 일치(exact match) 기준 precision/recall/F1/F2
- F2: 재현율에 F1보다 더 큰 가중치를 두는 지표(β=2) — PII 탐지는 미탐(FN)이 오탐(FP)보다
  위험하므로 F1과 함께 참고한다

## 종류(kind)별 결과

{_markdown_table(kind_results)}

## 난이도(difficulty)별 결과

{_markdown_table(difficulty_results)}

- `easy`: 하이픈 등 표준 구분자를 사용한 명확한 표기
- `hard`: 구분자 없음/국제표기/도로명+아파트 등 상대적으로 탐지가 어려운 표기
- `negative`: 개인정보가 전혀 없는(또는 distractor만 있는) 문서 — 오탐(FP) 측정용. 이 행은
  정답(tp가 될 대상)이 애초에 없어 precision/recall/F1/F2가 전부 0.000으로 찍히는데, 이는
  "탐지 실패"가 아니라 "계산이 성립하지 않음"이다(#498) — 이 행에서 의미 있는 값은 `fp`
  (오탐 건수) 하나뿐이다.
{_markdown_breakdown_section(breakdown)}"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


def main() -> None:
    """CLI 진입점 — 데이터셋을 읽어 kind별·difficulty별로 평가하고, 미탐·오탐을 유출 기준으로
    다시 나눈 표(#612)와 함께 콘솔에 찍은 뒤 --report가 있으면 같은 결과를 마크다운으로도 저장한다."""
    # #317: Windows 콘솔 기본 코드페이지(cp949)는 리포트 문구에 쓰일 수 있는 em dash(—) 등
    # 일부 구두점을 인코딩 못 해 print에서 크래시한다 — 플랫폼 기본 설정과 무관하게 항상
    # 성공하도록 stdout을 UTF-8로 강제한다.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="합성 데이터셋으로 탐지 정확도(F1) 평가")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    parser.add_argument("--report", type=Path, default=None, help="마크다운 리포트를 저장할 경로 (선택)")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    pipeline = Pipeline()
    kind_results = evaluate(rows, pipeline)
    difficulty_results = evaluate_by_difficulty(rows, pipeline)
    breakdown = breakdown_errors(rows, pipeline)
    print_report(kind_results, difficulty_results)
    print()
    print(format_breakdown_table(breakdown))

    if args.report:
        write_markdown_report(
            args.report, args.dataset, len(rows), kind_results, difficulty_results, breakdown
        )
        print(f"\n리포트 저장 완료: {args.report}")


if __name__ == "__main__":
    main()
