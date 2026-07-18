"""이메일 주소 탐지기 — 표준 형태의 이메일을 정규식으로 찾는다."""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+"  # 로컬 파트
    r"@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+"  # 도메인 라벨(점 포함) 반복
    r"[A-Za-z]{2,}"  # 최상위 도메인
)


class EmailDetector(Detector):
    """이메일 주소 탐지기."""

    kind = "email"

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind=self.kind,
                start=m.start(),
                end=m.end(),
                text=m.group(0),
                confidence=1.0,
                detector=self.__class__.__name__,
            )
            for m in _EMAIL_RE.finditer(text)
        ]
