"""신용카드번호 탐지기 — 그룹 구조 정규식 + Luhn 체크섬 검증.

동작 원리:
1. 실제 카드 표기(4-4-4-4=16, 4-6-5=15 Amex, 또는 붙여쓴 13~19 연속)를 정규식으로
   찾는다. 카드는 **4자리 그룹으로 시작**하므로 이를 정규식에 직접 표현한다.
2. 숫자만 뽑아 자릿수(13~19)를 확인하고 Luhn 알고리즘으로 검증한다 — 우연한 숫자열을
   걸러내 오탐을 줄인다(주민등록번호가 체크섬을 쓰는 것과 같은 방식).
3. 통과하면 확신도 0.95(체크섬이 있어도 우연히 맞을 수 있어 1.0은 아니다).

보안: 카드번호 누락은 금융정보 유출이다. 그룹 구조를 정규식에 담은 이유가 여기 있다.
- 예전엔 구분자로 공백을 관대하게 허용해, 카드 앞의 무관한 숫자("번호 123456 4242-...")를
  하나로 삼킨 뒤 검증 실패로 버리면서 **그 안의 진짜 카드를 놓쳤다**(finditer는 겹치지 않게
  진행하므로). 4자리 시작을 강제하면 앞 숫자를 삼키지 않아 카드를 놓치지 않는다.
- 4자리 시작 강제는 주민등록번호 6-7 표기("471534-3756648")도 자동으로 제외한다 —
  6자리로 시작하므로 카드 후보가 아니다(RRNDetector가 담당한다).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 카드는 4자리 그룹으로 시작한다. 이를 정규식에 직접 표현해 앞의 무관한 숫자를 삼키지
# 않고 주민등록번호 6-7 표기도 자연히 배제한다. 구분자는 하나로 일관되게 반복돼야 하며
# (역참조 \1), "4111 - 1111"처럼 공백을 낀 하이픈까지 담도록 자리당 1~3자를 허용한다.
# 개행은 구분자에 없어 서로 다른 줄의 숫자를 잇지 않는다. 반복·구분자에 상한을 둬 ReDoS를 막는다.
_CARD_RE = re.compile(
    r"(?<!\d)(?:"
    r"\d{4}([ .-]{1,3})\d{4}\1\d{4}\1\d{1,4}"  # 4-4-4-4 계열 (Visa/MC 등 16자리)
    r"|\d{4}([ .-]{1,3})\d{6}\2\d{5}"  # 4-6-5 (Amex 15자리)
    r"|\d{13,19}"  # 구분자 없이 붙여 쓴 13~19자리
    r")(?!\d)"
)


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
