# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""주민등록번호(RRN) 탐지기 — 정규식 + 유효성 검사.

동작 원리:
1. 정규식으로 "6자리-7자리" 형태의 후보를 찾는다 (구분자는 없거나 '-', '.', 공백).
   앞자리를 연도 네 자리로 쓴 "19800101-1234567"도 받는다(#508).
   뒷자리를 가려 적은 "800101-1******"·"800101-1"(성별 숫자만)도 받는다(#528) — 단,
   이 가려진/성별 숫자만 남은 뒷자리는 하이픈류 구분자가 있을 때만 받는다. 구분자를
   요구하지 않으면(공백이나 아예 없어도 됨) "주문번호 2409305"·"작성일 240101 3건"처럼
   날짜로 시작하는 무관한 숫자를 주민번호로 오탐한다(팀장 리뷰, PR #564).
2. 앞 6자리가 실제 존재하는 날짜인지 검사해 무작위 숫자열을 걸러낸다.
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

# 뒷자리가 실제 숫자 7개일 때의 구분자 — 하이픈/점/공백에 더해 en-dash·em-dash(Word·HWP
# 자동서식이 하이픈을 바꿈)와 "공백-하이픈-공백"·이중공백 같은 조합도 허용한다 — 상한
# {0,3}이라 ReDoS 없음. 이게 없으면 "800101 - 1234560"·"800101–1234560"에서 주민번호가
# 통째로 샌다(미탐=유출). 뒷자리가 완전한 숫자 7개일 때만 이렇게 느슨해도 된다 — 우연히
# 날짜 뒤에 무관한 숫자 7개가 이어질 확률은 낮기 때문이다.
_BACK_SEP = r"[-.\s–—]{0,3}"
_BACK = r"(?P<back>[1-8]\d{6})"

# 뒷자리가 가려졌거나(*, X, 동그라미 등) 성별 숫자만 남은 경우(#528)는 훨씬 흔한 문자열
# (날짜+건수 등)과 우연히 겹치기 쉬워, 구분자를 하이픈류 문자 하나로 좁힌다 — 공백만으로는
# 안 받는다. 그래야 "작성일 240101 3건"의 "3"을 성별 숫자로 오인하지 않는다.
_BACK_PARTIAL_SEP = r"[ \t]?[-–—‐－][ \t]?"
_BACK_PARTIAL = r"(?P<back_partial>[1-8](?:" + _MASK_CHAR + r"{1,6})?)"

# 6자리 생년월일 + (① 구분자 + 실제 숫자 7개 | ② 하이픈류 구분자 + 가려진/성별 숫자만
# 남은 뒷자리). 앞뒤에 숫자·영문이 더 붙으면 제외(다른 번호의 일부이거나 뒷자리가 더
# 남아있는 경우이므로). 앞에 연도 앞 두 자리(19·20)를 붙여 쓴 8자리 앞자리
# ("19800101-1234567")도 구간에 넣는다(#508). 생년월일 탐지기는 뒤에 뒷자리가 오는
# 8자리를 넘기므로, 여기서 안 잡으면 통째로 샌다.
_RRN_RE = re.compile(
    r"(?<!\d)(?:19|20)?(?P<front>\d{6})"
    r"(?:" + _BACK_SEP + _BACK + r"|" + _BACK_PARTIAL_SEP + _BACK_PARTIAL + r")"
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


def _checksum_ok(digits: str) -> bool:
    """13자리 전체의 검증 번호(마지막 자리)가 맞는지 확인한다."""
    total = sum(int(d) * w for d, w in zip(digits[:12], _WEIGHTS))
    return (11 - total % 11) % 10 == int(digits[12])


class RRNDetector(Detector):
    """주민등록번호(외국인등록번호 포함) 탐지기."""

    kind = "rrn"

    def detect(self, text: str) -> list[Detection]:
        """앞 6자리가 실제 날짜인지 먼저 거른다(_valid_birthdate).

        뒷자리 7개가 온전한 숫자일 때만 체크섬을 계산한다 — 맞으면 확신도 1.0, 틀리면
        0.85를 준다(2020년 10월 이후 발급분은 뒷자리가 난수라 체크섬이 없으므로 틀렸다고
        버리지 않는다). 뒷자리가 가려져 있거나 성별 숫자만 남아 체크섬 자체를 계산할 수
        없을 때도 0.85를 준다 — 형태(앞자리 날짜 + 성별 숫자)만으로 충분하다(#528).
        """
        found: list[Detection] = []
        for m in _RRN_RE.finditer(text):
            front = m.group("front")
            back = m.group("back") or m.group("back_partial")
            if not _valid_birthdate(front):
                continue
            if len(back) == 7 and back.isdigit():
                confidence = 1.0 if _checksum_ok(front + back) else 0.85
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
