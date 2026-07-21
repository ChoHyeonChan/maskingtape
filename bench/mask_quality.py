"""마스킹 결과 자체의 안전성을 검증한다 (탐지 정확도가 아니라 최종 산출물 검사).

동작 원리:
1. 정답 개인정보 값(gold span의 원문)이 마스킹된 텍스트 안에 문자 그대로 남아있는지 확인한다.
   하나라도 남아있으면 "유출"로 집계한다 — 탐지를 놓쳤든, 마스킹 로직에 버그가 있든 결과는 같다.
2. 마스킹 후 텍스트 길이가 원본과 같은지 확인한다 — MaskAnonymizer는 구간을 같은 길이의
   마스킹 문자로 치환하는 계약이므로, 길이가 달라지면 core에 회귀 버그가 생겼다는 신호다.

evaluate.py의 precision/recall이 "탐지기가 올바른 위치를 예측했는가"를 보는 내부 지표라면,
이 모듈은 "사용자가 받는 최종 결과물에 개인정보가 실제로 안 남았는가"를 보는 산출물 지표다.
"""

from __future__ import annotations

from dataclasses import dataclass

from maskingtape.pipeline import Pipeline


@dataclass(frozen=True)
class Leak:
    kind: str
    value: str


@dataclass
class MaskQualityResult:
    doc_count: int = 0
    gold_pii_count: int = 0
    leaks: list[Leak] | None = None
    length_mismatch_count: int = 0

    def __post_init__(self) -> None:
        if self.leaks is None:
            self.leaks = []

    @property
    def leak_count(self) -> int:
        return len(self.leaks)

    @property
    def leak_rate(self) -> float:
        return self.leak_count / self.gold_pii_count if self.gold_pii_count else 0.0

    @property
    def length_preserved_rate(self) -> float:
        return 1 - (self.length_mismatch_count / self.doc_count) if self.doc_count else 0.0


def evaluate_mask_quality(rows: list[dict], pipeline: Pipeline) -> MaskQualityResult:
    result = MaskQualityResult()
    for row in rows:
        original_text = row["text"]
        masked_text = pipeline.anonymize(original_text).text

        result.doc_count += 1
        if len(masked_text) != len(original_text):
            result.length_mismatch_count += 1

        for label in row["labels"]:
            result.gold_pii_count += 1
            gold_value = original_text[label["start"] : label["end"]]
            if gold_value and gold_value in masked_text:
                result.leaks.append(Leak(kind=label["kind"], value=gold_value))

    return result


def format_mask_quality_report(result: MaskQualityResult) -> str:
    lines = [
        "마스킹 품질 결과",
        "----------------",
        f"평가 문서 수:        {result.doc_count}",
        f"정답 개인정보 항목 수: {result.gold_pii_count}",
        f"유출 항목 수:        {result.leak_count} (유출률 {result.leak_rate:.1%})",
        f"길이 보존 문서 비율:  {result.length_preserved_rate:.1%} "
        f"(불일치 {result.length_mismatch_count}건 — 0이 아니면 core 마스킹 로직 버그 의심)",
    ]
    if result.leaks:
        by_kind: dict[str, int] = {}
        for leak in result.leaks:
            by_kind[leak.kind] = by_kind.get(leak.kind, 0) + 1
        lines.append("")
        lines.append("종류별 유출 건수:")
        for kind in sorted(by_kind):
            lines.append(f"  {kind}: {by_kind[kind]}건")
    return "\n".join(lines)
