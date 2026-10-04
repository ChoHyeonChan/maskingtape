# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""운전면허번호 탐지기 — 형식 + 지역코드 유효성.

동작 원리:
1. 12자리 숫자(지역코드 2 + 취득연도 2 + 일련번호 6 + 체크·회차 2)를 찾는다.
   구분자는 하이픈/공백/없음.
2. 앞 2자리 지역코드가 실제 발급 지역 코드(11~26, 28)인지 확인해 무작위 숫자열을 거른다.
3. 체크섬(검증번호) 알고리즘이 공개돼 있지 않아 형식+지역코드 유효성만으로 판단한다 —
   주민등록번호의 체크섬 없는 케이스처럼 확신도를 0.85로 준다(형식은 맞지만 확정은 아님).

출처: Microsoft Purview 운전면허증 번호 엔터티 정의(지역코드 유효값 11~26, 28).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 발급 지역코드(앞 2자리) 유효값: 11~26, 28. 무작위 12자리가 우연히 이 형식에 맞을 확률을 줄인다.
_REGION = r"(?:1[1-9]|2[0-6]|28)"

# 12자리: 지역코드 + 연도(2) + 일련(6) + 체크·회차(2). 구분자는 하이픈/공백/없음(선택).
# 앞뒤에 숫자·하이픈이 더 붙으면 더 긴 번호(카드·계좌 등)의 일부이므로 제외한다.
_DL_RE = re.compile(r"(?<![\d-])" + _REGION + r"[- ]?\d{2}[- ]?\d{6}[- ]?\d{2}(?![\d-])")

# 지역 이름으로 시작하는 옛 표기(#594) — 2014-06-01 발급분부터 앞 2자리가 숫자 지역코드로
# 바뀌었고, 그 전에는 지역 이름(시·도 줄임말)을 인쇄했다("경기 98-800924-64"). 이름은 숫자
# 코드와 1:1로 안 맞는 경우가 있어 목록을 임의로 늘리지 않는다 — 광주는 시험장이 없어
# 전남으로 발급됐고, 세종(27)·경기북부(28)는 2014년 숫자 표기 전환 이후에 생긴 코드라 그
# 이전 이름 표기 자체가 없다. 그래서 전환 당시 실제로 쓰이던 15개 지역 이름만 받는다.
#
# 출처: 도로교통공단 "운전면허번호 지역표기 변경 안내"(2014-06-01 시행, 외교부 재외국민
# 대상 공지 재게시) — https://overseas.mofa.go.kr/fi-ko/brd/m_9610/view.do?seq=1064435 ,
# https://poland.korean.net (주폴란드대사관, 동일 공지 재게시). 지역-코드 대응: 서울11·
# 부산12·경기13·강원14·충북15·충남16·전북17·전남18·경북19·경남20·제주21·대구22·인천23·
# 대전25·울산26. 광주는 운전면허시험장이 없어 전남(18)으로 발급된다고 명시돼 있다.
_REGION_NAMES = (
    "서울",
    "부산",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
    "대구",
    "인천",
    "대전",
    "울산",
)
_REGION_NAME_ALT = "|".join(_REGION_NAMES)

# 지역 이름 뒤엔 "YY-NNNNNN-NN"(연도 2 + 일련 6 + 체크·회차 2, 하이픈 고정)이 온다. 하이픈을
# 고정으로 요구하는 게 핵심 오탐 방지 장치다 — 전화번호("031-1234-5678")는 자리수가 3-4-4라
# 가운데에 연속 숫자 6개가 나올 수 없으므로 이 모양 자체에 안 맞아 저절로 걸러진다. 지역
# 이름 뒤에 다른 한글이 더 붙으면("경기도", 가상의 "경기북부") 이름이 아니라 더 긴 낱말의
# 일부이므로 막는다.
_DL_NAMED_RE = re.compile(
    r"(?<![가-힣])(?:" + _REGION_NAME_ALT + r")(?![가-힣])[ ]{0,2}\d{2}-\d{6}-\d{2}(?!\d)"
)


class DriverLicenseDetector(Detector):
    """운전면허번호 탐지기 (형식 + 지역코드 유효성, 체크섬 비공개라 confidence 0.85)."""

    kind = "driver_license"

    def detect(self, text: str) -> list[Detection]:
        """형식과 지역코드(숫자 또는 이름)가 맞는 번호를 확신도 0.85로 돌려준다.

        검증번호 알고리즘이 공개돼 있지 않아 형식만으로는 확정할 수 없다 — 지역 이름 표기도
        같은 이유로 같은 확신도를 쓴다. 가리는 범위는 지역 이름부터 끝 숫자까지다(#594) —
        지역 이름 자체가 발급 지역을 특정하는 정보라 라벨처럼 떼어내지 않는다.
        """
        found = [
            Detection(
                kind=self.kind,
                start=m.start(),
                end=m.end(),
                text=m.group(0),
                confidence=0.85,
                detector=self.__class__.__name__,
            )
            for m in _DL_RE.finditer(text)
        ]
        found.extend(
            Detection(
                kind=self.kind,
                start=m.start(),
                end=m.end(),
                text=m.group(0),
                confidence=0.85,
                detector=self.__class__.__name__,
            )
            for m in _DL_NAMED_RE.finditer(text)
        )
        found.sort(key=lambda d: d.start)
        return found
