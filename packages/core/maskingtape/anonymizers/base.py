"""마스킹 전략 공통 인터페이스.

새 전략 만드는 법:
1. 이 폴더에 파일 하나 추가 (전략 1종 = 파일 1개, 예: pseudonym.py)
2. Anonymizer를 상속하고 apply()를 구현 — mask.py가 참고 구현
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from maskingtape.types import Detection


class Anonymizer(ABC):
    """모든 마스킹 전략의 부모 클래스."""

    @abstractmethod
    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        """탐지 결과를 반영해 비식별화된 텍스트를 반환한다."""
