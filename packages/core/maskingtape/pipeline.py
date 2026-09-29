# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""탐지기 → 마스킹 전략을 조립하는 파이프라인. 조립만 담당하고 탐지 로직은 갖지 않는다."""

from __future__ import annotations

from dataclasses import dataclass

from maskingtape.anonymizers import Anonymizer, MaskAnonymizer
from maskingtape.detectors import Detector, default_detectors
from maskingtape.normalize import normalize
from maskingtape.overlaps import resolve_overlaps as _resolve_overlaps  # 옛 이름(벤치 테스트, #494)
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
        """detectors를 넘기지 않으면 규칙 탐지기 기본 세트(default_detectors, LLM 없음)를,
        anonymizer를 넘기지 않으면 '*' 마스킹을 쓴다. 기본값만으로 로컬 LLM 없이 동작한다.
        """
        self.detectors = detectors if detectors is not None else default_detectors()
        self.anonymizer = anonymizer if anonymizer is not None else MaskAnonymizer()

    def scan(self, text: str) -> list[Detection]:
        """마스킹 없이 탐지 결과만 반환한다.

        전각 숫자·폭 없는 공백·대시 변형·자모 분해처럼 표기를 정리하면 달라지는 입력은
        원문과 정리본 둘 다에서 찾아 합친다(#490). 원문 결과를 그대로 두므로 정리 때문에
        덜 가리는 일은 없다.

        모델을 부르는 탐지기(calls_model)는 비싸서 보통 정리본에서만 돌린다. 공백·대시·전각을
        바꾸거나 보이지 않는 문자만 지우는 정리는 이름 글자가 그대로라서다. 자모를 합치거나
        결합 부호를 지워 글자 자체가 바뀌는 정리에서는 원문에서도 돌린다 — 정리본에서는 모델이
        원문의 이름 모양을 볼 수 없어서다.
        """
        prepared = normalize(text)
        found: list[Detection] = []
        for detector in self.detectors:
            if prepared.text == text:
                found.extend(detector.detect(text))
                continue
            if not detector.calls_model or prepared.letters_changed:
                found.extend(detector.detect(text))
            found.extend(prepared.restore(d) for d in detector.detect(prepared.text))
        return _resolve_overlaps(found, text)

    def anonymize(self, text: str) -> AnonymizeResult:
        """탐지 후 마스킹까지 수행한다."""
        detections = self.scan(text)
        return AnonymizeResult(text=self.anonymizer.apply(text, detections), detections=detections)
