"""탐지기 → 마스킹 전략을 조립하는 파이프라인. 조립만 담당하고 탐지 로직은 갖지 않는다."""

from __future__ import annotations

from dataclasses import dataclass, replace

from maskingtape.anonymizers import Anonymizer, MaskAnonymizer
from maskingtape.detectors import Detector, default_detectors
from maskingtape.types import Detection


@dataclass(frozen=True)
class AnonymizeResult:
    """비식별화 결과 — 치환된 텍스트와 탐지 내역."""

    text: str
    detections: list[Detection]


class Pipeline:
    """탐지 → 겹침 정리 → 마스킹을 한 번에 수행한다."""

    def __init__(
        self,
        detectors: list[Detector] | None = None,
        anonymizer: Anonymizer | None = None,
    ) -> None:
        self.detectors = detectors if detectors is not None else default_detectors()
        self.anonymizer = anonymizer if anonymizer is not None else MaskAnonymizer()

    def scan(self, text: str) -> list[Detection]:
        """마스킹 없이 탐지 결과만 반환한다."""
        found: list[Detection] = []
        for detector in self.detectors:
            found.extend(detector.detect(text))
        return _resolve_overlaps(found, text)

    def anonymize(self, text: str) -> AnonymizeResult:
        """탐지 후 마스킹까지 수행한다."""
        detections = self.scan(text)
        return AnonymizeResult(text=self.anonymizer.apply(text, detections), detections=detections)


def _resolve_overlaps(detections: list[Detection], text: str) -> list[Detection]:
    """겹치는 탐지 구간을 **합친다**. 어느 쪽도 버리지 않는다.

    비식별화에서 '덜 가리는 것'은 개인정보 유출이고, '더 가리는 것'은 안전한 실패다.
    그래서 겹치면 넓은 쪽(합집합)으로 가리고, 종류(kind)만 확신도가 높은 쪽을 따른다.

    예전에는 겹치는 탐지를 통째로 버렸는데, 주소 탐지기가 뒤따르는 주민등록번호의 앞자리를
    번지로 삼켜 구간이 겹치면 **주민번호 탐지(확신도 1.0)가 사라져 뒷자리가 그대로 노출**됐다:
        "서울특별시 강남구 역삼동 800101-1234560" → "******************01-1234560"
    게다가 그때 scan()은 rrn을 보고하지 않아, 호출자는 주민번호가 없다고 통보받았다.
    """
    ordered = sorted(detections, key=lambda d: (d.start, -(d.end - d.start), -d.confidence))
    result: list[Detection] = []
    for d in ordered:
        if not result or d.start >= result[-1].end:
            result.append(d)
            continue

        previous = result[-1]
        if d.end <= previous.end:
            continue  # 앞의 구간이 이미 완전히 덮고 있다

        # 부분적으로 겹친다 — 가리는 범위는 합집합, 종류는 확신도가 높은 쪽을 남긴다
        winner = d if d.confidence > previous.confidence else previous
        result[-1] = replace(
            winner, start=previous.start, end=d.end, text=text[previous.start : d.end]
        )
    return result
