# SPDX-License-Identifier: Apache-2.0

"""생년월일 탐지기 — 문맥 앵커 + 날짜 유효성 검사.

동작 원리:
1. "생년월일/생일/출생일" 같은 라벨(앵커) 뒤에 오는 날짜만 잡는다. 앵커 없는 순수
   날짜("근무 개시일 2026년 3월 1일")는 잡지 않는다 — 일반 날짜와 구분하기 위함이다.
2. 날짜 형식은 "YYYY년 M월 D일"과 "YYYY-MM-DD"(구분자 -, ., /)를 지원한다.
3. 실제로 존재하는 날짜인지 검사해(13월·2월 30일 등) 무작위 숫자를 걸러낸다.

마스킹 대상은 날짜 값이므로 스팬은 날짜만 잡는다(앵커 라벨은 개인정보가 아니라 제외).
주민등록번호 앞자리와 직결되는 개인식별정보라, 놓치면 곧 유출이다.
"""

from __future__ import annotations

import re
from datetime import date

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 생년월일을 가리키는 라벨(앵커). 이 뒤에 오는 날짜만 생년월일로 본다 — 일반 날짜와 구분.
# 긴 것부터 둬야 "출생년월일"이 "출생"+"년월일"로 잘리지 않는다.
_ANCHOR = r"(?:출생년월일|생년월일|출생일|생일)"

# 날짜: "1999년 7월 21일"(사이 공백 유무 무관) 또는 "1999-07-21"(구분자 -, ., /).
_DATE = r"(?:\d{4}\s?년\s?\d{1,2}\s?월\s?\d{1,2}\s?일|\d{4}[-./]\d{1,2}[-./]\d{1,2})"

# 앵커와 날짜 사이엔 콜론·공백·조사(은/는/이/가)가 올 수 있다("생년월일은 ...", "생일: ...").
# 구분자엔 상한을 둔다({0,10}, {0,5}) — 무제한 `*` 두 개(`[\s:]*`+`\s*`)가 인접하면 같은 공백열을
# 두고 분할 경우의 수를 전수 역추적해 ReDoS(catastrophic backtracking)가 난다. 실제 표기에서
# 구분자는 짧으므로 상한으로 폭발을 막는다(rrn·email 등 다른 탐지기의 반복 상한 관례와 일치).
_BIRTHDATE_RE = re.compile(_ANCHOR + r"[\s:]{0,10}(?:은|는|이|가)?\s{0,5}(?P<date>" + _DATE + r")")


def _valid_date(date_str: str) -> bool:
    """날짜 문자열(년·월·일 숫자 3개)이 실제 존재하는 날짜인지 확인한다."""
    nums = re.findall(r"\d+", date_str)
    if len(nums) != 3:
        return False
    year, month, day = (int(n) for n in nums)
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


class BirthDateDetector(Detector):
    """생년월일 탐지기 (문맥 앵커 기반 — 일반 날짜와 구분)."""

    kind = "birth_date"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _BIRTHDATE_RE.finditer(text):
            date_text = m.group("date")
            if not _valid_date(date_text):
                continue
            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start("date"),
                    end=m.end("date"),
                    text=date_text,
                    confidence=0.9,
                    detector=self.__class__.__name__,
                )
            )
        return found
