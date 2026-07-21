"""마스킹 결과 자체의 안전성을 검증한다 (탐지 정확도가 아니라 최종 산출물 검사).

동작 원리:
1. 정답 개인정보 구간([start, end))의 각 글자 위치가 마스킹 후에도 원문 그대로인지 하나씩 비교한다.
   MaskAnonymizer는 구간 길이를 보존하는 계약이라, 길이가 같으면 같은 인덱스가 같은 글자 위치를
   가리킨다 — 그래서 위치별로 "이 글자가 바뀌었는가"만 보면 노출 비율을 정확히 계산할 수 있다.
2. 노출 비율이 1.0(전혀 안 가려짐)이면 "완전 유출", 0<비율<1.0이면 "부분 유출"(경계가 어긋나
   일부만 가려진 경우)로 구분한다 — 탐지는 됐지만 마스킹 범위가 정답과 다른 경우를 놓치지 않기 위함.
3. 마스킹 후 텍스트 길이가 원본과 같은지도 확인한다 — 길이가 달라지면 core에 회귀 버그가
   생겼다는 신호이며, 이 경우 위치 비교가 무의미해지므로 원문 전체 포함 여부로 보수적으로 판정한다.

evaluate.py의 precision/recall이 "탐지기가 올바른 위치를 예측했는가"를 보는 내부 지표라면,
이 모듈은 "사용자가 받는 최종 결과물에 개인정보가 실제로 얼마나 남았는가"를 보는 산출물 지표다.
"""

from __future__ import annotations

from dataclasses import dataclass

from maskingtape.pipeline import Pipeline


@dataclass(frozen=True)
class Leak:
    kind: str
    value: str
    exposed_ratio: float  # 0.0(완전 마스킹, 이 dataclass엔 안 담김)~1.0(완전 노출)

    @property
    def is_partial(self) -> bool:
        return self.exposed_ratio < 1.0


def _exposed_ratio(original_text: str, masked_text: str, start: int, end: int) -> float:
    """[start, end) 구간에서 원문 글자가 마스킹 후에도 그대로 남아있는 비율."""
    span_len = end - start
    if span_len <= 0:
        return 0.0
    exposed = sum(1 for i in range(start, end) if masked_text[i] == original_text[i])
    return exposed / span_len


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
        """조금이라도 노출된(exposed_ratio > 0) 항목 수 — 완전 유출 + 부분 유출."""
        return len(self.leaks)

    @property
    def full_leak_count(self) -> int:
        return sum(1 for leak in self.leaks if leak.exposed_ratio >= 1.0)

    @property
    def partial_leak_count(self) -> int:
        return sum(1 for leak in self.leaks if leak.is_partial)

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
        lengths_match = len(masked_text) == len(original_text)
        if not lengths_match:
            result.length_mismatch_count += 1

        for label in row["labels"]:
            result.gold_pii_count += 1
            start, end = label["start"], label["end"]
            gold_value = original_text[start:end]
            if not gold_value:
                continue

            if lengths_match:
                ratio = _exposed_ratio(original_text, masked_text, start, end)
            else:
                # 길이가 달라지면 위치 비교가 무의미하므로, 원문이 통째로 남아있는지만 보수적으로 본다.
                ratio = 1.0 if gold_value in masked_text else 0.0

            if ratio > 0:
                result.leaks.append(Leak(kind=label["kind"], value=gold_value, exposed_ratio=ratio))

    return result


def format_mask_quality_report(result: MaskQualityResult) -> str:
    lines = [
        "마스킹 품질 결과",
        "----------------",
        f"평가 문서 수:        {result.doc_count}",
        f"정답 개인정보 항목 수: {result.gold_pii_count}",
        f"유출 항목 수:        {result.leak_count} (유출률 {result.leak_rate:.1%}) "
        f"— 완전유출 {result.full_leak_count} / 부분유출 {result.partial_leak_count}",
        f"길이 보존 문서 비율:  {result.length_preserved_rate:.1%} "
        f"(불일치 {result.length_mismatch_count}건 — 0이 아니면 core 마스킹 로직 버그 의심)",
    ]
    if result.leaks:
        by_kind: dict[str, list[float]] = {}
        for leak in result.leaks:
            by_kind.setdefault(leak.kind, []).append(leak.exposed_ratio)
        lines.append("")
        lines.append("종류별 유출 건수 (평균 노출 비율):")
        for kind in sorted(by_kind):
            ratios = by_kind[kind]
            avg = sum(ratios) / len(ratios)
            lines.append(f"  {kind}: {len(ratios)}건 (평균 {avg:.0%} 노출)")
    return "\n".join(lines)
