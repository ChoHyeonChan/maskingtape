# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

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
- 카드 두 장이 이어지면(#510) 앞 카드의 뒤 묶음과 뒤 카드의 앞 묶음을 이은 숫자열이 Luhn을
  우연히 통과해 먼저 잡히고, finditer가 그 끝부터 다시 찾아 **진짜 뒤 카드를 검사하지 않았다**.
  그래서 매치마다 한 글자만 넘기고 다시 찾는다(_search_every_start) — 겹치는 창을 모두 후보로
  보고, 통과한 것을 Pipeline이 합친다(더 가리기=안전).
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 카드는 4자리 그룹으로 시작한다. 이를 정규식에 직접 표현해 앞의 무관한 숫자를 삼키지
# 않고 주민등록번호 6-7 표기도 자연히 배제한다. 구분자는 하나로 일관되게 반복돼야 하며
# (역참조 \1), "4111 - 1111"처럼 공백을 낀 하이픈까지 담도록 자리당 1~3자를 허용한다.
# 개행은 구분자에 없어 서로 다른 줄의 숫자를 잇지 않는다. 반복·구분자에 상한을 둬 ReDoS를 막는다.
# 모양마다 따로 찾는다(#493). 한 정규식의 선택지로 두면 먼저 맞은 모양이 자리를 차지해,
# 19자리 모양이 "16자리 카드 + 뒤의 숫자 3개"를 삼킨 뒤 체크섬에서 버려지면 16자리 카드를 놓친다.
_CARD_SHAPES = (
    r"\d{4}([ .-]{1,3})\d{4}\1\d{4}\1\d{1,4}",  # 4-4-4-4 계열 (Visa/MC 등 16자리)
    r"\d{4}([ .-]{1,3})\d{6}\1\d{5}",  # 4-6-5 (Amex 15자리)
    r"\d{13,19}",  # 구분자 없이 붙여 쓴 13~19자리
    r"\d{4}([ .-]{1,3})\d{4}\1\d{4}\1\d{4}\1\d{1,3}",  # 4-4-4-4-3 (17~19자리, #493)
    r"\d{4}([ .-]{1,3})\d{6}\1\d{4}",  # 4-6-4 (Diners 14자리, #493)
)
_CARD_RES = tuple(re.compile(r"(?<!\d)(?:" + shape + r")(?!\d)") for shape in _CARD_SHAPES)
# 하이픈·공백을 섞어 쓴 16자리("4111-1111 1111-1111", #493). 연도 목록("2023-2024 2025-2026")도
# 같은 모양이라 Luhn이 우연히 맞으면 카드가 되므로, 앞에 카드 문맥어가 있을 때만 받는다.
_MIXED_CARD_RE = re.compile(r"(?<!\d)\d{4}[ -]{1,3}\d{4}[ -]{1,3}\d{4}[ -]{1,3}\d{4}(?!\d)")
# 신용카드·체크카드는 "카드"로 잡힌다. "신용"·"체크"만 두면 "신용등급"·"체크리스트" 뒤 연도 목록도 받는다.
_CARD_CUE_RE = re.compile(r"카드|card|결제", re.IGNORECASE)
_CARD_CUE_WINDOW = 15
# 카드 종류 라벨이 번호 바로 앞에 있으면 Luhn이 틀려도 받는다(#607). 손으로 옮기다 한 자리 틀리거나
# OCR로 잘못 읽은 번호도 라벨이 "카드번호다"라고 말해 주므로 번호 전체를 가린다. 체크섬이 없는
# 경우라 확신도는 계좌와 같은 0.6이다. 라벨 없이 형식만 맞는 숫자열은 여전히 버린다(#87).
_CARD_LABEL_BEFORE_RE = re.compile(
    r"(?:신용카드|체크카드|법인카드|카드 ?번호)[ \t]{0,3}[:：]?[ \t]{0,3}\Z"
)
_CARD_LABEL_WINDOW = 20
_LABELED_CONFIDENCE = 0.6
# 섞인 모양이 이미 찾은 카드 바로 뒤에 이어지면(구분자만 사이에 둠) 앞 카드의 문맥을 물려받는다(#510).
# "카드 4111-1111 1111-1111 4111-1111 1111-1111"의 둘째 카드는 "카드"가 15자 밖이라 통째로 남았다.
# 사이에 글자가 끼면 이어진 목록이 아니므로 받지 않는다 — 연도 목록 오탐 방지는 그대로다.
_ADJACENT_GAP_RE = re.compile(r"[ ,/]{1,3}")
# 이어받기로 받을 때만, 네 묶음이 모두 연도처럼 생긴 것(19xx·20xx)은 연도 목록으로 보고 받지 않는다.
# 차등 검사에서 "카드번호 바로 뒤의 1999-2009 2014-2004"가 Luhn이 우연히 맞아 카드로 잡히는 오탐이
# 나왔다. 실제 카드의 네 묶음이 모두 1900~2099일 일은 사실상 없다. 문맥어 경로에는 쓰지 않는다.
_YEAR_LIST_RE = re.compile(r"(?:19|20)\d\d(?:[ -]{1,3}(?:19|20)\d\d){3}")


def _search_every_start(pattern: re.Pattern[str], text: str) -> Iterator[re.Match[str]]:
    """매치마다 한 글자만 넘기고 다시 찾는다 — 겹치는 창도 모두 후보로 본다(#510).

    주소 탐지기의 같은 이름 함수(#465)와 같은 방식이다. finditer는 매치가 끝난 자리부터 다시
    찾아서, 매치 안에서 시작하는 진짜 카드를 시도조차 하지 않는다. 각 모양 정규식은 앞뒤에
    숫자가 붙어 있지 않아야 한다는 경계 검사가 있어 숫자 묶음 중간에서는 시작하지 않으므로,
    후보 수는 묶음 수를 넘지 않는다.
    """
    pos = 0
    while (m := pattern.search(text, pos)) is not None:
        yield m
        pos = m.start() + 1


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
        """그룹 구조에 맞는 후보에서 숫자만 뽑아 자릿수(13~19)와 Luhn 체크섬을 확인한다.

        체크섬이 우연히 맞을 수도 있어 확신도는 1.0이 아니라 0.95다. Luhn이 틀려도 카드 라벨이
        바로 앞에 있으면 0.6으로 받는다(#607).
        """
        found: list[Detection] = []
        seen: set[tuple[int, int]] = set()
        # (매치, 섞인 모양인가). 섞인 모양의 문맥 확인은 아래 루프에서 한다 — 앞 카드를
        # 이어받는지 보려면 이미 받은 카드를 알아야 해서다.
        matches = [(m, False) for regex in _CARD_RES for m in _search_every_start(regex, text)]
        matches += [(m, True) for m in _search_every_start(_MIXED_CARD_RE, text)]
        for m, mixed in sorted(matches, key=lambda pair: pair[0].span()):
            digits = re.sub(r"\D", "", m.group(0))
            if not (13 <= len(digits) <= 19) or m.span() in seen:
                continue
            if _luhn_ok(digits):
                if mixed and not self._has_card_context(text, m, found):
                    continue
                confidence = 0.95
            elif self._has_card_label(text, m):
                confidence = _LABELED_CONFIDENCE
            else:
                continue
            seen.add(m.span())
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

    @staticmethod
    def _has_card_label(text: str, match: re.Match[str]) -> bool:
        """번호 바로 앞(공백·쌍점 몇 자 이내)에 카드 종류 라벨이 있는지 본다(#607)."""
        start = match.start()
        return (
            _CARD_LABEL_BEFORE_RE.search(text, max(0, start - _CARD_LABEL_WINDOW), start)
            is not None
        )

    @staticmethod
    def _has_card_context(text: str, match: re.Match[str], found: list[Detection]) -> bool:
        """섞인 모양 후보가 카드 문맥에 있는지 — 앞 15자 안 문맥어, 또는 이미 찾은 카드 바로 뒤."""
        start = match.start()
        if _CARD_CUE_RE.search(text, max(0, start - _CARD_CUE_WINDOW), start):
            return True
        if _YEAR_LIST_RE.fullmatch(match.group(0)):
            return False
        return any(
            d.end <= start and _ADJACENT_GAP_RE.fullmatch(text, d.end, start) for d in found
        )
