"""주민등록번호(RRN) 탐지기 — 정규식 + 유효성 검사.

동작 원리:
1. 정규식으로 "6자리-7자리" 형태의 후보를 찾는다 (구분자는 없거나 '-' 또는 공백).
2. 앞 6자리가 실제 존재하는 날짜인지 검사해 무작위 숫자열을 걸러낸다.
3. 검증 번호(체크섬)까지 맞으면 확신도 1.0, 아니면 0.85로 낮춘다.
   2020년 10월 이후 발급분은 뒷자리가 난수라 체크섬이 없으므로 탈락시키지 않는다.
"""

from __future__ import annotations

import re
from datetime import date

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 6자리 생년월일 + 구분자 + 성별코드(1~8) + 6자리. 앞뒤에 숫자가 더 붙으면 제외.
_RRN_RE = re.compile(r"(?<!\d)(\d{6})[-\s]?([1-8]\d{6})(?!\d)")

# 7번째 자리(성별코드) → 출생 세기. 5~8은 외국인등록번호 계열.
_CENTURY = {"1": 1900, "2": 1900, "3": 2000, "4": 2000, "5": 1900, "6": 1900, "7": 2000, "8": 2000}

# 체크섬 가중치 (앞 12자리에 곱한 뒤 11로 나눈 나머지로 검증 번호 계산)
_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)


def _valid_birthdate(front: str, gender_code: str) -> bool:
    """앞 6자리가 성별코드 기준 세기에서 실제 날짜인지 확인한다."""
    century = _CENTURY[gender_code]
    try:
        date(century + int(front[0:2]), int(front[2:4]), int(front[4:6]))
    except ValueError:
        return False
    return True


def _checksum_ok(digits: str) -> bool:
    """13자리 전체의 검증 번호(마지막 자리)가 맞는지 확인한다."""
    total = sum(int(d) * w for d, w in zip(digits[:12], _WEIGHTS))
    return (11 - total % 11) % 10 == int(digits[12])


class RRNDetector(Detector):
    """주민등록번호(외국인등록번호 포함) 탐지기."""

    kind = "rrn"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _RRN_RE.finditer(text):
            front, back = m.group(1), m.group(2)
            if not _valid_birthdate(front, back[0]):
                continue
            confidence = 1.0 if _checksum_ok(front + back) else 0.85
            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    confidence=confidence,
                    detector=self.__class__.__name__,
                )
            )
        return found
