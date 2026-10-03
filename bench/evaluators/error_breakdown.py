# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""미탐·오탐을 "유출인가" 기준으로 다시 나눈다(#612).

evaluate.py는 예측과 정답이 (종류, 시작, 끝)까지 완전히 같을 때만 맞은 것으로 센다. 그래서
"환자 권연의"에서 정답 `권연`을 `권연의`로 한 글자 더 가린 것(유출 없음)과, 이름을 아예 못
찾은 것(유출)이 똑같이 미탐 1건으로 찍힌다. 이 모듈은 그 미탐·오탐을 성격별로 나눈다.

미탐(정답 기준, 정답의 종류로 집계):
- 가려짐(fn_covered): 정답 구간의 모든 글자를 예측이 덮는다. 경계나 종류만 다르다 — 유출 없음.
- 부분 유출(fn_partial): 일부 글자만 덮는다. 남은 글자가 원문으로 남는다.
- 완전 유출(fn_missed): 겹치는 예측이 하나도 없다.

오탐(예측 기준, 예측의 종류로 집계):
- 경계 불일치(fp_boundary): 어떤 정답과 겹친다. 위 "가려짐"·"부분 유출"의 반대쪽이다.
- 엉뚱한 곳(fp_spurious): 어떤 정답과도 겹치지 않는다. 개인정보가 아닌 곳을 가렸다.

덮였는지는 종류와 무관하게 본다 — 주소로 가려졌든 이름으로 가려졌든 글자는 안 보인다.
세 미탐 분류의 합은 evaluate.py의 fn과, 두 오탐 분류의 합은 fp와 항상 같다(테스트로 확인).
"""

from __future__ import annotations

from dataclasses import dataclass

from maskingtape.pipeline import Pipeline


@dataclass
class ErrorBreakdown:
    tp: int = 0
    fn_covered: int = 0
    fn_partial: int = 0
    fn_missed: int = 0
    fp_boundary: int = 0
    fp_spurious: int = 0

    @property
    def fn(self) -> int:
        return self.fn_covered + self.fn_partial + self.fn_missed

    @property
    def fp(self) -> int:
        return self.fp_boundary + self.fp_spurious

    @property
    def leak_recall(self) -> float:
        """유출 기준 재현율 — 정답 가운데 글자가 전부 가려진 비율((적중 + 가려짐) / 정답 수).
        정답이 하나도 없으면 ZeroDivisionError 대신 0.0을 돌려준다(evaluate.Counts와 같은 규칙)."""
        total = self.tp + self.fn
        return (self.tp + self.fn_covered) / total if total else 0.0

    def add(self, other: ErrorBreakdown) -> None:
        self.tp += other.tp
        self.fn_covered += other.fn_covered
        self.fn_partial += other.fn_partial
        self.fn_missed += other.fn_missed
        self.fp_boundary += other.fp_boundary
        self.fp_spurious += other.fp_spurious


def _covered_chars(start: int, end: int, spans: list[tuple[int, int]]) -> int:
    """[start, end) 가운데 spans가 덮는 글자 수. 예측 둘이 나눠 덮어도 합쳐서 센다."""
    return sum(1 for i in range(start, end) if any(s <= i < e for s, e in spans))


def breakdown_errors(rows: list[dict], pipeline: Pipeline) -> dict[str, ErrorBreakdown]:
    """종류(kind)별 ErrorBreakdown을 돌려준다. 전체 합계는 `__overall__` 키에 넣는다."""
    per_kind: dict[str, ErrorBreakdown] = {}
    for row in rows:
        gold = {(lb["kind"], lb["start"], lb["end"]) for lb in row["labels"]}
        pred = {(d.kind, d.start, d.end) for d in pipeline.scan(row["text"])}
        pred_spans = [(s, e) for _, s, e in pred]
        gold_spans = [(s, e) for _, s, e in gold]

        for kind, start, end in gold:
            counts = per_kind.setdefault(kind, ErrorBreakdown())
            if (kind, start, end) in pred:
                counts.tp += 1
                continue
            covered = _covered_chars(start, end, pred_spans)
            if covered == end - start:
                counts.fn_covered += 1
            elif covered:
                counts.fn_partial += 1
            else:
                counts.fn_missed += 1

        for kind, start, end in pred - gold:
            counts = per_kind.setdefault(kind, ErrorBreakdown())
            if _covered_chars(start, end, gold_spans):
                counts.fp_boundary += 1
            else:
                counts.fp_spurious += 1

    overall = ErrorBreakdown()
    for counts in per_kind.values():
        overall.add(counts)
    per_kind["__overall__"] = overall
    return per_kind


_COLUMNS = ("가려짐", "부분 유출", "완전 유출", "경계 불일치", "엉뚱한 곳")


def _cells(c: ErrorBreakdown) -> tuple[int, ...]:
    return (c.fn_covered, c.fn_partial, c.fn_missed, c.fp_boundary, c.fp_spurious)


def format_breakdown_table(results: dict[str, ErrorBreakdown]) -> str:
    """콘솔용 표. 한글 열 이름은 폭이 맞지 않아, 숫자 열은 영문 약어로 찍고 아래에 뜻을 적는다."""
    results = dict(results)
    overall = results.pop("__overall__")
    title = "미탐·오탐 분해 (유출 기준)"
    header = (
        f"{'group':<16} {'fn':>4} {'covered':>8} {'partial':>8} {'missed':>7} "
        f"{'fp':>4} {'boundary':>9} {'spurious':>9} {'leak_recall':>12}"
    )
    lines = [title, "-" * len(title), header]
    for group in sorted(results) + ["overall"]:
        c = overall if group == "overall" else results[group]
        if group == "overall":
            lines.append("-" * len(header))
        lines.append(
            f"{group:<16} {c.fn:>4} {c.fn_covered:>8} {c.fn_partial:>8} {c.fn_missed:>7} "
            f"{c.fp:>4} {c.fp_boundary:>9} {c.fp_spurious:>9} {c.leak_recall:>12.3f}"
        )
    lines.append(
        "covered=가려짐(경계·종류만 다름, 유출 없음) / partial=부분 유출 / missed=완전 유출 / "
        "boundary=정답과 겹치는 오탐 / spurious=엉뚱한 곳을 가린 오탐"
    )
    return "\n".join(lines)


def markdown_breakdown_table(results: dict[str, ErrorBreakdown]) -> str:
    """마크다운 리포트용 표 — format_breakdown_table과 같은 내용이다."""
    results = dict(results)
    overall = results.pop("__overall__")
    lines = [
        "| group | 미탐(fn) | " + " | ".join(_COLUMNS[:3]) + " | 오탐(fp) | " + " | ".join(_COLUMNS[3:])
        + " | 유출 기준 재현율 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for group in sorted(results):
        c = results[group]
        covered, partial, missed, boundary, spurious = _cells(c)
        lines.append(
            f"| {group} | {c.fn} | {covered} | {partial} | {missed} | {c.fp} | {boundary} | {spurious} "
            f"| {c.leak_recall:.3f} |"
        )
    covered, partial, missed, boundary, spurious = _cells(overall)
    lines.append(
        f"| **overall** | {overall.fn} | {covered} | {partial} | {missed} | {overall.fp} | {boundary} "
        f"| {spurious} | **{overall.leak_recall:.3f}** |"
    )
    return "\n".join(lines)
