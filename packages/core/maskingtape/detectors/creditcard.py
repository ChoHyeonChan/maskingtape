"""신용카드번호 탐지기 — 정규식 + Luhn 체크섬 검증.

동작 원리:
1. 13~19자리 숫자(구분자는 없거나 '-'·공백)를 정규식으로 찾는다. 반복에는 상한을 둬
   ReDoS를 막고, 앞뒤에 숫자가 더 붙으면(전화번호 등의 일부) 제외한다.
2. 숫자만 뽑아 자릿수(13~19)를 확인하고, 구분자로 끊은 자릿수가 6-7이면 주민등록번호
   표기이므로 제외한다(카드는 6-7로 끊지 않는다).
3. Luhn 알고리즘으로 검증한다 — 우연한 숫자열을 걸러내 오탐을 줄인다(주민등록번호가
   체크섬을 쓰는 것과 같은 방식). 통과하면 확신도 0.95(체크섬이 있어도 우연히 맞을 수
   있어 1.0은 아니다).

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

# 구분자로 끊어 쓴 자릿수가 6-7이면 주민등록번호·외국인등록번호 표기다. 13자리라 카드
# 자릿수 범위에 들어오고 Luhn을 우연히 통과하기도 하지만(약 1/10), 6-7로 끊는 카드는 없다.
# 실제 카드 표기는 4-4-4-4(16), 4-6-5(15, Amex)처럼 항상 4자리로 시작한다.
# 이 형식을 제외해도 놓치는 개인정보는 없다 — RRNDetector가 외국인등록번호(성별코드 5~8)까지
# 잡고, 체크섬이 틀려도 생년월일만 유효하면 확신도 0.85로 남긴다. 생년월일까지 무효인
# 문자열은 애초에 주민등록번호가 아니다.
_ID_NUMBER_GROUPS = [6, 7]


def _group_lengths(raw: str) -> list[int]:
    """구분자로 끊긴 숫자 묶음의 자릿수 — "4111-1111-1111-1111" → [4, 4, 4, 4]."""
    return [len(part) for part in re.split(r"[ .-]+", raw) if part]


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
            if _group_lengths(m.group(0)) == _ID_NUMBER_GROUPS:
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
