"""신용카드번호 탐지기 — 정규식 + Luhn 체크섬 검증.

동작 원리:
1. 13~19자리 숫자(구분자는 없거나 '-'·공백)를 정규식으로 찾는다. 반복에는 상한을 둬
   ReDoS를 막고, 앞뒤에 숫자가 더 붙으면(전화번호 등의 일부) 제외한다.
2. 숫자만 뽑아 자릿수(13~19)를 확인하고 Luhn 알고리즘으로 검증한다 — 우연한 숫자열을
   걸러내 오탐을 줄인다(주민등록번호가 체크섬을 쓰는 것과 같은 방식).
3. Luhn을 통과하면 확신도 0.95를 준다(체크섬이 있어도 우연히 맞을 수 있어 1.0은 아니다).

보안: 카드번호 누락은 금융정보 유출이다. 구분자 유무를 넉넉히 허용해(4-4-4-4, 공백,
붙여쓰기) 놓치지 않는 것을 우선한다.
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 숫자로 시작·끝나고, 사이에 숫자/구분자가 이어지는 뭉치. 앞뒤에 숫자가 더 붙으면 제외.
# 구분자는 공백·점·하이픈을 자리당 최대 3개까지 허용한다("4111.1111", "4111 - 1111" 등 실제 표기).
# 개행(\n)은 넣지 않는다 — 서로 다른 줄의 무관한 숫자를 카드로 잘못 잇는 오탐을 막는다.
# 반복과 구분자 개수 모두 상한을 둬 ReDoS를 막는다(자릿수 검증은 아래에서 다시 한다).
_CARD_RE = re.compile(r"(?<!\d)\d(?:[ .-]{0,3}\d){12,18}(?!\d)")


def _luhn_ok(digits: str) -> bool:
    """Luhn 체크섬 검증 — 카드번호가 만족해야 하는 표준 검사."""
    total = 0
    # 오른쪽 끝(체크 숫자)부터 왼쪽으로, 두 번째 자리마다 2배(9 초과면 -9)
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


class CreditCardDetector(Detector):
    """신용카드번호 탐지기 (Luhn 체크섬 검증)."""

    kind = "card"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _CARD_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if not (13 <= len(digits) <= 19):
                continue
            if not _luhn_ok(digits):
                continue
            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    confidence=0.95,
                    detector=self.__class__.__name__,
                )
            )
        return found
