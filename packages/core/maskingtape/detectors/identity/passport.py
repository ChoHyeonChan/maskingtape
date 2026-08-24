# SPDX-License-Identifier: Apache-2.0

"""여권번호 탐지기 — 정규식 + 문맥어.

동작 원리:
1. 정규식으로 대한민국 여권번호 형식을 찾는다(외교부 차세대 전자여권 / MS Purview 확인).
   - 구여권: 문자(M/S/R/O/D) + 8자리 숫자 — M12345678
   - 신여권(차세대): 문자 + 3자리 + 문자 + 4자리 — M123A4567
2. 여권번호는 검증 체크섬이 **없다** — 그래서 문맥어("여권")가 가까이 있으면 확신도를
   높이고(0.9), 형식만이면 낮게(0.6) 준다. 낮아도 마스킹은 되므로(과탐=안전) 임계값으로
   조절할 수 있다.
3. 앞뒤에 다른 영숫자가 붙으면(더 긴 코드의 일부) 제외한다.

여권번호는 개인정보보호법상 고유식별정보다(identity/ 도메인).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 구여권 M12345678 / 신여권 M123A4567. 허용 문자는 M/S/R/O/D(여권 종류 코드).
# 앞뒤 영숫자가 붙으면 더 긴 문자열의 일부이므로 제외한다.
_PASSPORT_RE = re.compile(r"(?<![A-Za-z0-9])[MSROD](?:\d{8}|\d{3}[A-Z]\d{4})(?![A-Za-z0-9])")

# 문맥어가 앞쪽 이 글자수 안에 있으면 여권번호일 확신이 높다.
_CONTEXT_WINDOW = 15


class PassportDetector(Detector):
    """대한민국 여권번호 탐지기 (구·신 여권 형식)."""

    kind = "passport"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _PASSPORT_RE.finditer(text):
            context = text[max(0, m.start() - _CONTEXT_WINDOW) : m.start()]
            confidence = 0.9 if "여권" in context else 0.6
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
