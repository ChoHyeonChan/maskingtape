# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""주민등록번호(RRN) 탐지기 — 정규식 + 유효성 검사.

동작 원리:
1. 정규식으로 "6자리-7자리" 형태의 후보를 찾는다.
   앞자리를 연도 네 자리로 쓴 "19800101-1234567"도 받는다(#508).
   앞자리를 점·하이픈으로 나눠 쓴 "1980.01.01"·"1980-01-01"(생년월일 날짜 표기)도
   받는다(#529) — 뒤에 뒷자리가 이어지면 이 형태도 주민등록번호 앞자리일 수 있다.
   뒷자리가 실제 숫자 7개일 때는 구분자를 넓게 받는다(하이픈·점·공백에 더해 슬래시·
   밑줄·쉼표·쌍점·가운뎃점·물결·세로줄 등 #529, 가운뎃점과 닮은 점 문자 #631). 뒷자리를 가려 적은 "800101-1******"·
   "800101-1"(성별 숫자만, #528)일 때는 구분자를 하이픈류 문자 하나로 좁힌다 — 느슨하게
   두면 "주문번호 2409305"·"작성일 240101 3건"처럼 날짜로 시작하는 무관한 숫자를
   주민번호로 오탐한다(팀장 리뷰, PR #564 후속).
2. 앞자리가 실제 존재하는 날짜인지 검사해 무작위 숫자열을 걸러낸다.
3. 검증 번호(체크섬)까지 맞으면 확신도 1.0, 틀리면 0.85로 낮춘다. 뒷자리가 가려져
   체크섬을 계산할 수 없을 때도 0.85를 준다 — 형태만으로 충분히 주민등록번호다(#528).
   2020년 10월 이후 발급분은 뒷자리가 난수라 체크섬이 없으므로 탈락시키지 않는다.
"""

from __future__ import annotations

import re
from datetime import date

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 뒷자리를 가릴 때 쓰는 문자들 — 별표·영문 X·검은/흰 동그라미·네모·샵. 성별 숫자 뒤에
# 1~6개 올 수 있다(#528). 실제 숫자 7개가 온전히 남아 있으면 아래 쪽 대안이 그걸 잡는다.
_MASK_CHAR = r"[*Xx●○■#]"

# 앞자리 — 붙여 쓴 6자리(성별코드 앞의 생년월일)나 연도 앞 두 자리(19·20)를 더 붙인 8자리
# (#508)에 더해, 점·하이픈으로 나눠 쓴 "1980.01.01"·"1980-01-01"(생년월일 날짜 표기,
# #529)도 받는다 — "생년월일 1980.01.01-1234567"처럼 날짜 표기 뒤에 주민등록번호 뒷자리가
# 바로 이어지는 문서가 실제로 있다.
_FRONT_PLAIN = r"(?:19|20)?(?P<front>\d{6})"
_FRONT_DATED = r"(?P<front_dated>\d{4}[.\-]\d{2}[.\-]\d{2})"

# 뒷자리가 실제 숫자 7개일 때의 구분자 — 하이픈/점/공백에 더해 en-dash·em-dash(Word·HWP
# 자동서식이 하이픈을 바꿈), 슬래시·밑줄·쉼표·쌍점·가운뎃점(·, ㆍ, ‧)·물결·세로줄까지
# 받는다(#529 — #508 독립 검증에서 이 문자들로 구분한 표기가 원문 그대로 새는 것을
# 찾았다). "공백-하이픈-공백"처럼 구분자가 여러 글자 겹치는 표기까지 보려고 상한을
# {0,4}로 둔다 — 상한이 있으니 ReDoS 없음. 뒷자리가 완전한 숫자 7개일 때만 이렇게
# 느슨해도 된다 — 우연히 날짜 뒤에 무관한 숫자 7개가 이어질 확률은 낮기 때문이다.
# 가운뎃점과 모양이 비슷한 점 문자도 받는다(#631 — 목록에 없어 번호가 통째로 샜다):
# 가타카나 가운뎃점(전각·반각), 글머리 기호, 글머리 연산자, 점 연산자, 한 점 리더, 작은
# 마침표, Z 표기 점, 검은 동그라미, 세딜라, 윗점. 눈으로 헷갈리므로 코드값으로 적는다.
_DOT_LIKE = "\u30fb\uff65\u2022\u2219\u22c5\u2024\ufe52\u2981\u25cf\u00b8\u02d9"
_BACK_SEP = r"[-.\s–—/_,:·ㆍ‧~|" + _DOT_LIKE + r"]{0,4}"
_BACK = r"(?P<back>[1-8]\d{6})"

# 생년월일 탐지기가 날짜 뒤에 주민등록번호 뒷자리가 이어지는지 볼 때 쓴다. 아래 _RRN_RE의
# 첫 갈래(구분자 + 실제 숫자 7개 + 끝 경계)와 글자 하나까지 같아야 한다 — 생년월일 쪽이
# 넘긴 자리를 여기서 받지 않으면 두 탐지기 모두 버려 통째로 새고(#508), 여기서 받는
# 구분자를 생년월일 쪽이 모르면 체크섬이 안 맞는 번호의 종류가 생년월일로 바뀐다(#631).
# 뒷자리가 가려졌거나(*, X, 동그라미 등) 성별 숫자만 남은 경우(#528)는 훨씬 흔한 문자열
# (날짜+건수 등)과 우연히 겹치기 쉬워, 구분자를 하이픈류 문자 하나로 좁힌다 — 공백만으로는
# 안 받는다. 그래야 "작성일 240101 3건"의 "3"을 성별 숫자로 오인하지 않는다(팀장 리뷰,
# PR #564 후속).
_BACK_PARTIAL_SEP = r"[ \t]?[-–—‐－][ \t]?"
# 뒷자리 일부만 적고 나머지를 가린 표기("19800101-1234***", #637)도 받는다 — 성별 숫자 뒤에
# 실제 숫자가 0~6개 오고 그 뒤에 가림 문자가 0~6개 온다. 점·하이픈 날짜와 붙여 쓴 날짜 모두 앞자리가
# 실제 날짜일 때만 받으므로, 날짜가 아닌 숫자 뒤의 하이픈 번호는 여전히 버린다.
_BACK_PARTIAL_BODY = r"[1-8]\d{0,6}(?:" + _MASK_CHAR + r"{0,6})?"
_BACK_PARTIAL = r"(?P<back_partial>" + _BACK_PARTIAL_BODY + r")"

# 뒷자리 7자리 바로 뒤에 영문 한 글자가 붙은 표기("800101-1234560A", #640)는 받되, 그 영문 뒤에
# 영숫자가 더 이어지면 긴 영숫자 코드의 일부이므로 받지 않는다.
_TRAILING_LETTER = r"(?:[A-Za-z](?![A-Za-z\d]|-[A-Za-z\d]))?"
RRN_BACK_AHEAD = (
    r"(?:" + _BACK_SEP + r"[1-8]\d{6}" + _TRAILING_LETTER + r"|" + _BACK_PARTIAL_SEP
    + _BACK_PARTIAL_BODY + r")(?![\dA-Za-z])"
)

# (① 붙여 쓴 6·8자리 앞자리 | ② 점·하이픈 날짜 앞자리) + (① 구분자(넓게) + 실제 숫자
# 7개 | ② 하이픈류 구분자(좁게) + 가려진/성별 숫자만 남은 뒷자리). 앞뒤에 숫자·영문이
# 더 붙으면 제외(다른 번호의 일부이거나 뒷자리가 더 남아있는 경우이므로). 생년월일
# 탐지기는 뒤에 뒷자리가 오는 8자리를 넘기므로, 여기서 안 잡으면 통째로 샌다.
_RRN_RE = re.compile(
    r"(?<!\d)(?:" + _FRONT_PLAIN + r"|" + _FRONT_DATED + r")"
    r"(?:" + _BACK_SEP + _BACK + _TRAILING_LETTER + r"|" + _BACK_PARTIAL_SEP + _BACK_PARTIAL + r")"
    r"(?![\dA-Za-z])"
)

# 체크섬 가중치 (앞 12자리에 곱한 뒤 11로 나눈 나머지로 검증 번호 계산)
_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)


def _valid_birthdate(front: str) -> bool:
    """앞 6자리가 1900년대나 2000년대 가운데 하나에서 실제 날짜인지 확인한다.

    성별코드로 세기를 하나만 정하지 않는다. 생년월일 탐지기는 뒤에 뒷자리가 오는 날짜를 이
    탐지기에 넘기고, 2자리 연도를 두 세기 모두로 검사한다. 여기가 더 좁으면 "000229 1234567"
    (1900년 2월 29일은 없다)처럼 두 탐지기 모두 버려서 통째로 샌다(#508).
    """
    for century in (1900, 2000):
        try:
            date(century + int(front[0:2]), int(front[2:4]), int(front[4:6]))
        except ValueError:
            continue
        return True
    return False


def _valid_dated_front(front_dated: str) -> bool:
    """"1980.01.01"·"1980-01-01"처럼 점·하이픈으로 나눠 쓴 4자리 연도 앞자리가 실제 존재하는
    날짜인지 확인한다(#529). 4자리 연도가 이미 있으므로 두 세기를 다 시도할 필요는 없다."""
    year, month, day = (int(part) for part in re.split(r"[.\-]", front_dated))
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


_RRN_LABEL_RE = re.compile(r"주민|생년월일|출생|생일")
_RRN_LABEL_WINDOW = 20


def _partial_back_ok(text: str, match: re.Match[str], back: str) -> bool:
    """일부만 적은 뒷자리를 받을지 본다(#637).

    가림 문자가 있거나 성별 숫자 하나만 있으면 받는다. 가림 문자 없이 실제 숫자 2~6개만 적은
    꼴은 8자리 앞자리(19·20으로 시작하는 생년월일)이면서 앞에 주민번호·생년월일 라벨이 있을
    때만 받는다. "ORD-20250408-2110"·"240101-1234" 같은 날짜형 주문·운송장 번호에 흔해서,
    라벨 없이 받으면 오탐이 크다.
    """
    if re.search(_MASK_CHAR, back) or len(back) == 1:
        return True
    eight_digit_front = match.group("front") is not None and match.start("front") > match.start()
    if not eight_digit_front:
        return False
    start = match.start()
    return _RRN_LABEL_RE.search(text, max(0, start - _RRN_LABEL_WINDOW), start) is not None


def _checksum_front(front: str | None, front_dated: str | None) -> str:
    """체크섬 계산용 앞 6자리(YYMMDD)를 얻는다 — 점·하이픈 표기는 4자리 연도의 뒤 2자리만 쓴다."""
    if front is not None:
        return front
    year, month, day = re.split(r"[.\-]", front_dated)  # type: ignore[arg-type]
    return year[-2:] + month + day


def _checksum_ok(digits: str) -> bool:
    """13자리 전체의 검증 번호(마지막 자리)가 맞는지 확인한다."""
    total = sum(int(d) * w for d, w in zip(digits[:12], _WEIGHTS))
    return (11 - total % 11) % 10 == int(digits[12])


class RRNDetector(Detector):
    """주민등록번호(외국인등록번호 포함) 탐지기."""

    kind = "rrn"

    def detect(self, text: str) -> list[Detection]:
        """앞자리가 실제 날짜인지 먼저 거른다(_valid_birthdate / _valid_dated_front).

        뒷자리 7개가 온전한 숫자일 때만 체크섬을 계산한다 — 맞으면 확신도 1.0, 틀리면
        0.85를 준다(2020년 10월 이후 발급분은 뒷자리가 난수라 체크섬이 없으므로 틀렸다고
        버리지 않는다). 뒷자리가 가려져 있거나 성별 숫자만 남아 체크섬 자체를 계산할 수
        없을 때도 0.85를 준다 — 형태(앞자리 날짜 + 성별 숫자)만으로 충분하다(#528).
        """
        found: list[Detection] = []
        for m in _RRN_RE.finditer(text):
            front, front_dated = m.group("front"), m.group("front_dated")
            back = m.group("back")
            if back is None:
                back = m.group("back_partial")
                if not _partial_back_ok(text, m, back):
                    continue
            if front is not None:
                if not _valid_birthdate(front):
                    continue
            elif not _valid_dated_front(front_dated):
                continue
            if len(back) == 7 and back.isdigit():
                confidence = 1.0 if _checksum_ok(_checksum_front(front, front_dated) + back) else 0.85
            else:
                confidence = 0.85
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
