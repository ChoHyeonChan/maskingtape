# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""주민등록번호(RRN) 탐지기 — 정규식 + 유효성 검사.

동작 원리:
1. 정규식으로 "6자리-7자리" 형태의 후보를 찾는다 (구분자는 하이픈·점·공백을 비롯해
   슬래시·밑줄·가운뎃점 등 드문 표기도 받는다).
   앞자리를 연도 네 자리로 쓴 "19800101-1234567"도 받는다(#508).
   뒷자리를 가려 적은 "800101-1******"·"800101-1"(성별 숫자만)도 받는다(#528).
   앞자리를 점·하이픈으로 나눠 쓴 "1980.01.01"·"1980-01-01"(생년월일 날짜 표기)도
   받는다(#529) — 뒤에 뒷자리가 이어지면 이 형태도 주민등록번호 앞자리일 수 있다.
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

# 앞자리와 뒷자리 사이 구분자 — 하이픈/점/공백에 더해 en-dash·em-dash(Word·HWP 자동서식이
# 하이픈을 바꿈), 슬래시·밑줄·쉼표·쌍점·가운뎃점(·, ㆍ, ‧)·물결·세로줄까지 받는다(#529 —
# #508 독립 검증에서 이 문자들로 구분한 표기가 원문 그대로 새는 것을 찾았다). "공백-하이픈-
# 공백"처럼 구분자가 여러 글자 겹치는 표기까지 보려고 상한을 {0,3}에서 {0,4}로 늘렸다 —
# 상한이 있으니 여전히 ReDoS 없음.
_SEP = r"[-.\s–—/_,:·ㆍ‧~|]{0,4}"

# 앞자리 — 붙여 쓴 6자리(성별코드 앞의 생년월일)나 연도 앞 두 자리(19·20)를 더 붙인 8자리
# (#508)에 더해, 점·하이픈으로 나눠 쓴 "1980.01.01"·"1980-01-01"(생년월일 날짜 표기,
# #529)도 받는다 — "생년월일 1980.01.01-1234567"처럼 날짜 표기 뒤에 주민등록번호 뒷자리가
# 바로 이어지는 문서가 실제로 있다.
_FRONT_PLAIN = r"(?:19|20)?(?P<front>\d{6})"
_FRONT_DATED = r"(?P<front_dated>\d{4}[.\-]\d{2}[.\-]\d{2})"

# 성별코드(1~8) + (실제 6자리 | 가려진 뒷자리 1~6개 | 아무것도 없음). 앞뒤에 숫자·영문이
# 더 붙으면 제외(다른 번호의 일부이거나 뒷자리가 더 남아있는 경우이므로). 이게 없으면
# "800101 - 1234560"·"800101–1234560"에서 주민번호가 통째로 샌다(미탐=유출). 생년월일
# 탐지기는 뒤에 뒷자리가 오는 8자리를 넘기므로, 여기서 안 잡으면 통째로 샌다. 성별 숫자만
# 남기고 뒷자리를 통째로 가리거나 아예 안 적은 표기("800101-1")도 뒤에 숫자·영문이 더 안
# 붙을 때로 한정해 받는다 — 그래야 앞자리(생년월일)까지 통째로 새는 걸 막는다(#528).
_BACK = r"(?P<back>[1-8](?:\d{6}|" + _MASK_CHAR + r"{1,6})?)"

_RRN_RE = re.compile(r"(?<!\d)(?:" + _FRONT_PLAIN + r"|" + _FRONT_DATED + r")" + _SEP + _BACK + r"(?![\dA-Za-z])")

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
            front, front_dated, back = m.group("front"), m.group("front_dated"), m.group("back")
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
