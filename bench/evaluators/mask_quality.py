"""마스킹 결과 자체의 안전성을 검증한다 (탐지 정확도가 아니라 최종 산출물 검사).

동작 원리:
1. mask 전략은 정답 개인정보 구간([start, end))의 각 글자 위치가 마스킹 후에도 원문 그대로인지
   하나씩 비교한다. MaskAnonymizer는 구간 길이를 보존하는 계약이라, 길이가 같으면 같은 인덱스가
   같은 글자 위치를 가리킨다 — 그래서 위치별 비교로 노출 비율(부분 유출까지)을 정확히 계산할 수 있다.
2. label/pseudonym 전략은 구간을 통째로 다른 내용(라벨·가짜 값)으로 바꿔치기해 위치 비교 가정이
   깨지므로(예: 가짜 전화번호가 항상 "010-"로 시작해 우연히 원문과 같은 위치가 겹칠 수 있음),
   원문이 결과에 통째로 남아있는지만 본다 — 완전 유출/무유출 둘 중 하나로만 판정한다.
3. 마스킹 후 텍스트 길이가 원본과 같은지도 확인한다 — mask 전략에서만 길이 불일치가 core 회귀
   버그 신호이고, label/pseudonym은 길이가 달라지는 게 정상이라 참고 정보로만 취급한다.

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
    strategy: str = "mask"

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


def evaluate_mask_quality(rows: list[dict], pipeline: Pipeline, strategy: str = "mask") -> MaskQualityResult:
    """strategy에 따라 유출 판정 방식이 달라진다 — "mask"만 자리별 비교가 성립한다.

    위치별 문자 비교(_exposed_ratio)는 "같은 위치는 안 바뀐 원문"이라는 가정에 기대는데, 이건
    MaskAnonymizer가 구간을 제자리에서 같은 길이로 치환한다는 계약을 지킬 때만 성립한다.
    label/pseudonym은 구간을 통째로 다른 내용으로 바꿔치기하므로 이 가정이 깨진다 — 예를 들어
    가짜 전화번호가 항상 "010-"로 시작하면, 원문도 "010-"로 시작할 때 우연히 같은 위치의
    문자가 일치해 실제로는 안 새어나간 값이 "부분 유출"로 오판된다(실측으로 확인한 문제).
    그래서 "mask"만 위치 비교를 쓰고, 나머지는 원문 전체가 결과에 통째로 남아있는지만 본다
    (부분 유출 개념 자체가 없음 — label/pseudonym은 구간을 전부 바꾸거나 전혀 안 바꾸거나 둘 중 하나).
    """
    result = MaskQualityResult(strategy=strategy)
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

            if strategy == "mask" and lengths_match:
                ratio = _exposed_ratio(original_text, masked_text, start, end)
            else:
                # 위치 비교가 성립하지 않는 경우(mask가 아니거나 길이가 다름) — 원문이
                # 통째로 남아있는지만 본다.
                ratio = 1.0 if gold_value in masked_text else 0.0

            if ratio > 0:
                result.leaks.append(Leak(kind=label["kind"], value=gold_value, exposed_ratio=ratio))

    return result


def format_mask_quality_report(result: MaskQualityResult) -> str:
    if result.strategy == "mask":
        length_note = "0이 아니면 core 마스킹 로직 버그 의심 — mask는 구간 길이를 보존하는 계약"
    else:
        length_note = f"{result.strategy} 전략은 원본과 길이가 달라지는 게 정상이라 참고용 수치"

    title = f"마스킹 품질 결과 (전략: {result.strategy})"
    lines = [
        title,
        "-" * len(title),
        f"평가 문서 수:        {result.doc_count}",
        f"정답 개인정보 항목 수: {result.gold_pii_count}",
        f"유출 항목 수:        {result.leak_count} (유출률 {result.leak_rate:.1%}) "
        f"— 완전유출 {result.full_leak_count} / 부분유출 {result.partial_leak_count}",
        f"길이 보존 문서 비율:  {result.length_preserved_rate:.1%} "
        f"(불일치 {result.length_mismatch_count}건 — {length_note})",
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
