"""탐지 결과를 표현하는 공용 타입.

모든 탐지기(detectors)와 마스킹 전략(anonymizers)이 이 타입으로 대화한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """텍스트에서 발견된 개인정보 한 건.

    kind: 개인정보 종류 (예: "rrn", "phone", "name")
    start/end: 원문 기준 위치 (파이썬 슬라이스 규약 — text[start:end] == text)
    text: 매칭된 원문 조각
    confidence: 탐지 확신도 0.0~1.0
    detector: 탐지기 이름 (디버깅·리포트용)
    """

    kind: str
    start: int
    end: int
    text: str
    confidence: float = 1.0
    detector: str = ""
