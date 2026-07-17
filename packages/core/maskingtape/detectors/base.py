"""탐지기 공통 인터페이스.

새 탐지기 만드는 법:
1. 이 폴더에 파일 하나 추가 (탐지기 1종 = 파일 1개, 예: phone.py)
2. Detector를 상속하고 kind와 detect()를 구현 — rrn.py가 참고 구현
3. detectors/__init__.py의 default_detectors()에 등록
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from maskingtape.types import Detection


class Detector(ABC):
    """모든 탐지기의 부모 클래스."""

    #: 이 탐지기가 찾는 개인정보 종류 (Detection.kind에 그대로 들어간다)
    kind: str = ""

    @abstractmethod
    def detect(self, text: str) -> list[Detection]:
        """text에서 개인정보를 찾아 Detection 목록으로 반환한다."""
