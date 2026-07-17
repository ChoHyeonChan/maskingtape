"""탐지기 → 마스킹 전략을 조립하는 파이프라인. 조립만 담당하고 탐지 로직은 갖지 않는다."""

from __future__ import annotations

from dataclasses import dataclass

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
        return _resolve_overlaps(found)

    def anonymize(self, text: str) -> AnonymizeResult:
        """탐지 후 마스킹까지 수행한다."""
        detections = self.scan(text)
        return AnonymizeResult(text=self.anonymizer.apply(text, detections), detections=detections)


def _resolve_overlaps(detections: list[Detection]) -> list[Detection]:
    """겹치는 탐지 구간은 (긴 구간, 높은 확신도) 우선으로 하나만 남긴다."""
    ordered = sorted(detections, key=lambda d: (d.start, -(d.end - d.start), -d.confidence))
    result: list[Detection] = []
    for d in ordered:
        if result and d.start < result[-1].end:
            continue
        result.append(d)
    return result
