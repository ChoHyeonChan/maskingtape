# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""생년월일 탐지기 — 문맥 앵커 + 날짜 유효성 검사.

동작 원리:
1. "생년월일/생일/출생일" 같은 라벨(앵커) 뒤에 오는 날짜만 잡는다. 앵커 없는 순수
   날짜("근무 개시일 2026년 3월 1일")는 잡지 않는다 — 일반 날짜와 구분하기 위함이다.
2. 날짜 형식은 "YYYY년 M월 D일"과 "YYYY-MM-DD"(구분자 -, ., /), 그리고 서식·표에서 흔한
   2자리 연도 "YY.MM.DD"(#399)를 지원한다. 2자리 연도는 앵커가 있을 때만 잡는다 — 앵커 없이
   잡으면 일반 숫자·버전·날짜와 광범위하게 겹친다.
3. 실제로 존재하는 날짜인지 검사해(13월·2월 30일 등) 무작위 숫자를 걸러낸다.

마스킹 대상은 날짜 값이므로 스팬은 날짜만 잡는다(앵커 라벨은 개인정보가 아니라 제외).
주민등록번호 앞자리와 직결되는 개인식별정보라, 놓치면 곧 유출이다.
"""

from __future__ import annotations

import re
from datetime import date

from maskingtape.detectors.base import Detector
from maskingtape.detectors.identity.rrn import RRN_BACK_AHEAD
from maskingtape.types import Detection

# 생년월일을 가리키는 라벨(앵커). 이 뒤에 오는 날짜만 생년월일로 본다 — 일반 날짜와 구분.
# 긴 것부터 둬야 "출생년월일"이 "출생"+"년월일"로 잘리지 않는다. "출생"·"생년"만 쓴 서식도
# 흔하다(#493). 뒤에 실제 날짜가 와야 하므로 "출생 신고는 …" 같은 문장은 잡히지 않는다.
_ANCHOR = r"(?:출생년월일|생년월일|출생일|생일|출생|생년)"

# 날짜: "1999년 7월 21일"(사이 공백 유무 무관), "99년 7월 21일"(2자리 연도, #493),
# "1999-07-21"(구분자 -, ., /, 공문서처럼 구분자 앞뒤 공백·끝 마침표 "1999. 7. 21." 포함, #493),
# 붙여 쓴 "19990721"·"990721"(#493), "99.07.21"(2자리 연도).
# 4자리 연도를 먼저 시도해 "1999.07.21"의 "99.07.21"만 잘라 잡는 일이 없게 한다. 숫자가 더
# 이어지면("95.03.221", 주민등록번호 13자리) 날짜가 아니므로 (?!\d)로 막는다. 붙여 쓴 8자리는
# 뒤에 "-숫자"가 와도 막는다. 붙여 쓴 6자리와 19·20으로 시작하는 8자리는 뒤에 주민등록번호 뒷자리
# 모양(rrn.py의 RRN_BACK_AHEAD — 그쪽이 받는 구분자 + [1-8]로 시작하는 7자리 + 끝 경계를 그대로
# 가져다 쓴다, #631)이 오면 막는다 — "800101 1234567"·
# "19800101 1234567"은 주민등록번호 앞자리다(8자리는 #508). 생년월일로 잡으면 뒷자리 7개가 새고,
# 체크섬이 안 맞는 주민등록번호(2020년 10월 이후 번호 대부분)가 생년월일 확신도에 밀려 종류가 바뀐다.
# 8자리는 rrn.py가 받는 19·20으로 시작할 때만 넘긴다. "18991231 1234567"까지 넘기면 rrn.py가 받지
# 않아 두 탐지기 모두 버리고 통째로 샌다(#508 독립 검증).
_DATE = (
    r"(?:\d{4}\s?년\s?\d{1,2}\s?월\s?\d{1,2}\s?일"
    r"|\d{2}\s?년\s?\d{1,2}\s?월\s?\d{1,2}\s?일"
    r"|\d{4}\s{0,2}[-./]\s{0,2}\d{1,2}\s{0,2}[-./]\s{0,2}\d{1,2}(?:\.(?!\d))?"
    r"|(?:19|20)\d{6}(?!-?\d|" + RRN_BACK_AHEAD + r")"
    r"|(?!19|20)\d{8}(?!-?\d)"
    r"|\d{2}[-./]\d{1,2}[-./]\d{1,2}(?!\d)"
    r"|\d{6}(?!\d|" + RRN_BACK_AHEAD + r"))"
)

# 앵커와 날짜 사이엔 괄호 설명("(YYYY-MM-DD)", 숫자 없음, "(만 나이)(한국식)"처럼 세 개까지, #508/#529)·
# 콜론·표 칸 세로줄·공백·조사(은/는/이/가)가 올 수 있다("생년월일은 ...", "생일: ...", "| 생년월일 | ...").
# 괄호 앞에도 공백이 올 수 있다("생년월일 (만 나이) (한국식)", #529) — 붙여 쓴 표기만 받으면
# 라벨과 괄호 사이에 공백이 있는 흔한 표기를 놓친다. 구분자엔 상한을 둔다({0,3}, {0,10}, {0,5}) —
# 무제한 `*` 두 개(`[\s:]*`+`\s*`)가 인접하면 같은 공백열을 두고 분할 경우의 수를 전수 역추적해
# ReDoS(catastrophic backtracking)가 난다. 실제 표기에서 구분자는 짧으므로 상한으로 폭발을
# 막는다(rrn·email 등 다른 탐지기의 반복 상한 관례와 일치).
_BIRTHDATE_RE = re.compile(
    _ANCHOR
    + r"(?:\s{0,3}\([^()\d]{1,15}\)){0,3}[\s:|]{0,10}(?:은|는|이|가)?\s{0,5}(?P<date>"
    + _DATE
    + r")"
)

# 날짜 뒤에 오는 생년월일 단서(#592) — "1992년 10월 31일생입니다", "92년 7월 3일생이에요",
# "2019년 4월 23일에 태어났어요", "1995년 6월 21일이 제 생일이에요"처럼 말로 할 때는 라벨이
# 날짜보다 먼저 오지 않고, "생"·"태어"·"생일" 같은 단서가 날짜 뒤에 붙는 어순이 더 흔하다.
# "생"은 뒤에 특정 종결 어미가 없으면 "생산"·"생활"·"생각"·"생기다"·"생명" 같은 낱말의
# 앞부분과 구별이 안 된다 — 그래서 흔한 종결 어미 화이트리스트를 두고, 그 뒤에 한글이 더
# 이어지면("생산"의 "산") 실패하도록 (?![가-힣])로 막는다. 세 단서 모두 반복에 상한을 둔다
# (ReDoS 방지, 위 _BIRTHDATE_RE 주석과 같은 관례).
_TRAILING_CUE = (
    r"(?:생(?:이에요|이었|이고|이야|이다|이네요|이죠|입니다|으로)?(?![가-힣])"
    r"|에\s{0,2}태어"
    r"|(?:이|가)?\s{0,2}(?:제\s{0,2})?생일)"
)

_BIRTHDATE_TRAILING_RE = re.compile(r"(?P<date>" + _DATE + r")" + _TRAILING_CUE)


def _valid_date(date_str: str) -> bool:
    """날짜 문자열(년·월·일 숫자 3개)이 실제 존재하는 날짜인지 확인한다."""
    nums = re.findall(r"\d+", date_str)
    if len(nums) == 1 and len(nums[0]) in (6, 8):
        # 붙여 쓴 "19990721"·"990721" — 뒤에서부터 일(2)·월(2)을 떼고 남은 앞이 연도다
        compact = nums[0]
        nums = [compact[:-4], compact[-4:-2], compact[-2:]]
    if len(nums) != 3:
        return False
    year, month, day = (int(n) for n in nums)
    # 2자리 연도는 어느 세기인지 알 수 없다(95→1995, 04→2004). 유효성 판정에 세기가 영향을 주는
    # 건 2월 29일뿐이라, 1900년대·2000년대 중 하나라도 실제 날짜면 통과시킨다(더 가리기=안전).
    candidates = [year] if len(nums[0]) == 4 else [1900 + year, 2000 + year]
    for y in candidates:
        try:
            date(y, month, day)
            return True
        except ValueError:
            continue
    return False


class BirthDateDetector(Detector):
    """생년월일 탐지기 (문맥 앵커 기반 — 일반 날짜와 구분)."""

    kind = "birth_date"

    def detect(self, text: str) -> list[Detection]:
        """앵커(앞) 또는 단서(뒤) 곁의 날짜 가운데 실제로 있는 날짜만 확신도 0.9로 돌려준다.

        구간은 날짜 부분만 잡는다. 앵커·단서('생년월일'·'생'·'태어'·'생일' 등)는 개인정보가
        아니라서 가리지 않는다. 라벨이 앞에 오든(#493) 뒤에 오든(#592) 식별력은 같으므로
        확신도는 같은 0.9를 쓴다. 두 정규식이 같은 날짜를 중복으로 잡을 수 있어 스팬으로
        걸러낸다.
        """
        found: list[Detection] = []
        seen: set[tuple[int, int]] = set()
        for pattern in (_BIRTHDATE_RE, _BIRTHDATE_TRAILING_RE):
            for m in pattern.finditer(text):
                date_text = m.group("date")
                span = (m.start("date"), m.end("date"))
                if span in seen or not _valid_date(date_text):
                    continue
                seen.add(span)
                found.append(
                    Detection(
                        kind=self.kind,
                        start=span[0],
                        end=span[1],
                        text=date_text,
                        confidence=0.9,
                        detector=self.__class__.__name__,
                    )
                )
        found.sort(key=lambda d: d.start)
        return found
