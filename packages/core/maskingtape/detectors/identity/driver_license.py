# SPDX-License-Identifier: Apache-2.0

"""운전면허번호 탐지기 — 형식 + 지역코드 유효성.

동작 원리:
1. 12자리 숫자(지역코드 2 + 취득연도 2 + 일련번호 6 + 체크·회차 2)를 찾는다.
   구분자는 하이픈/공백/없음.
2. 앞 2자리 지역코드가 실제 발급 지역 코드(11~26, 28)인지 확인해 무작위 숫자열을 거른다.
3. 체크섬(검증번호) 알고리즘이 공개돼 있지 않아 형식+지역코드 유효성만으로 판단한다 —
   주민등록번호의 체크섬 없는 케이스처럼 확신도를 0.85로 준다(형식은 맞지만 확정은 아님).

출처: Microsoft Purview 운전면허증 번호 엔터티 정의(지역코드 유효값 11~26, 28).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 발급 지역코드(앞 2자리) 유효값: 11~26, 28. 무작위 12자리가 우연히 이 형식에 맞을 확률을 줄인다.
_REGION = r"(?:1[1-9]|2[0-6]|28)"

# 12자리: 지역코드 + 연도(2) + 일련(6) + 체크·회차(2). 구분자는 하이픈/공백/없음(선택).
# 앞뒤에 숫자·하이픈이 더 붙으면 더 긴 번호(카드·계좌 등)의 일부이므로 제외한다.
_DL_RE = re.compile(r"(?<![\d-])" + _REGION + r"[- ]?\d{2}[- ]?\d{6}[- ]?\d{2}(?![\d-])")


class DriverLicenseDetector(Detector):
    """운전면허번호 탐지기 (형식 + 지역코드 유효성, 체크섬 비공개라 confidence 0.85)."""

    kind = "driver_license"

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind=self.kind,
                start=m.start(),
                end=m.end(),
                text=m.group(0),
                confidence=0.85,
                detector=self.__class__.__name__,
            )
            for m in _DL_RE.finditer(text)
        ]
