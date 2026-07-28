"""사업자등록번호 탐지기 — 정규식 + 체크섬 검증.

동작 원리:
1. 정규식으로 "3-2-5" 하이픈 표기(XXX-XX-XXXXX)의 후보를 찾는다. 앞뒤에 숫자가
   더 붙으면(더 긴 숫자열의 일부) 제외한다.
2. 국세청 검증 알고리즘(가중치 1,3,7,1,3,7,1,3,5 + 9번째 자리 보정)으로 마지막
   검증 자리를 확인한다.
3. **체크섬이 맞는 번호만** 탐지한다(확신도 1.0). 체크섬 없는 3-2-5 숫자는 버린다 —
   주민번호(6-7 표기)와 달리 사업자번호는 예외 없이 모두 체크섬이 있어, 체크섬이 곧
   판별 기준이다. (실측: bench의 체크섬 없는 3-2-5 난수 12건이 오탐되던 것을 막는다.)

사업자등록번호는 개인정보보호법상 '개인 고유식별정보'는 아니지만(사업자=기관 식별),
개인사업자는 개인과 연결되고 계약서·세금계산서에 흔히 등장해 마스킹 대상이다.
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# XXX-XX-XXXXX (3-2-5) 하이픈 표기. 앞뒤에 숫자가 더 붙으면 더 긴 숫자열이므로 제외.
_BRN_RE = re.compile(r"(?<!\d)(\d{3})-(\d{2})-(\d{5})(?!\d)")

# 국세청 검증 가중치 — 앞 9자리에 곱한다.
_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 5)


def _checksum_ok(digits: str) -> bool:
    """10자리 전체의 검증 번호(마지막 자리)가 맞는지 확인한다.

    가중합에 9번째 자리×5의 십의 자리를 더한 뒤, 10에서 일의 자리를 뺀 값이
    마지막 자리와 같으면 유효하다.
    """
    total = sum(int(digits[i]) * _WEIGHTS[i] for i in range(9))
    total += (int(digits[8]) * 5) // 10
    return (10 - total % 10) % 10 == int(digits[9])


class BusinessRegistrationDetector(Detector):
    """사업자등록번호(XXX-XX-XXXXX) 탐지기."""

    kind = "biz_reg"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _BRN_RE.finditer(text):
            digits = m.group(1) + m.group(2) + m.group(3)
            if not _checksum_ok(digits):
                continue  # 체크섬 없는 3-2-5 숫자는 사업자번호가 아니다
            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    confidence=1.0,
                    detector=self.__class__.__name__,
                )
            )
        return found
