"""주소 탐지기 — 시/도명을 기준으로 지번·도로명 주소 패턴을 찾는다.

동작 원리:
1. 시/도명(사전 기반, 신구 행정명 모두 포함)이 나오면 후보로 삼는다.
2. 뒤에 시/군/구(2단계까지), 읍/면/동/리 또는 도로명, 번지(건물번호), 건물명+동/호가
   순서대로 이어지는지 확인하고 이어지는 만큼 구간을 넓힌다.
3. 매칭된 구성 요소가 많을수록(시/도만 vs 동/번지/건물까지 전부) 확신도를 높인다.
   "서울특별시청"처럼 시/도명이 다른 단어의 일부일 뿐이면 매칭하지 않는다.

구간을 끝까지 넓히는 게 핵심이다. 시/도만 가리고 "월드컵로237길 49 ..."를 남기면
개인정보 가치가 가장 낮은 부분만 가린 셈이라 사실상 유출이다(이슈 #66).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

_PROVINCES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원특별자치도",
    "강원도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
    "제주도",
]

# 긴 이름부터 매칭해야 "전라북도"가 "전북특별자치도" 매칭을 가로채지 않는다.
_PROVINCE_RE = "|".join(sorted(_PROVINCES, key=len, reverse=True))

_ADDR_RE = re.compile(
    # 시/도명 바로 뒤에 공백 없이 한글이 이어지면("서울특별시청") 다른 단어의 일부이므로 제외한다.
    # gu/dong/bunji 뒤에 조사가 공백 없이 붙는 건 정상 한국어("...123-4에 거주")이므로 막지 않는다.
    r"(?P<province>" + _PROVINCE_RE + r")(?![가-힣])"
    # 시/군/구는 두 단계까지 이어진다 — "성남시 분당구", "수원시 영통구".
    r"(?:\s(?P<gu>[가-힣]{1,10}[시군구]))?"
    r"(?:\s(?P<gu2>[가-힣]{1,10}[군구]))?"
    # 지번은 동/읍/면/리로 끝나지만, 도로명은 "월드컵로237길"처럼 가지번호가 공백 없이 붙는다.
    r"(?:\s(?P<dong>[가-힣]{1,10}(?:동|읍|면|리)|[가-힣]{1,10}(?:로|길)(?:\s?\d{1,4}번?길)?))?"
    # 번지 뒤에 숫자·하이픈이 더 이어지면 번지가 아니라 더 긴 숫자열(주민등록번호·전화번호)의
    # 일부다. 그걸 삼키면 주소 구간이 그 번호와 겹쳐 번호 탐지를 방해하므로 여기서 끊는다.
    r"(?:\s(?P<bunji>\d{1,4}(?:-\d{1,4})?)(?![\d-])(?:\s?호)?)?"
    # 건물명과 동/호까지 가려야 세대가 특정되지 않는다 — "더샵아파트 123동 1241호".
    # 건물명이 없어도("... 49 123동 1241호") 동/호는 각각 독립적으로 이어붙인다.
    r"(?:\s(?P<building>[0-9A-Za-z가-힣]{1,20}(?:아파트|빌라|오피스텔|맨션|타워)))?"
    r"(?:\s(?P<building_dong>\d{1,4}동))?"
    r"(?:\s(?P<building_ho>\d{1,5}호))?"
)


class AddressDetector(Detector):
    """한국 행정구역 주소 탐지기 (시/도 단위부터 번지까지)."""

    kind = "address"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _ADDR_RE.finditer(text):
            confidence = 0.5  # 시/도만 매칭돼도 최소 신뢰도는 준다
            if m.group("gu"):
                confidence += 0.15
            if m.group("gu2"):
                confidence += 0.05
            if m.group("dong"):
                confidence += 0.15
            if m.group("bunji"):
                confidence += 0.2
            if m.group("building"):
                confidence += 0.15
            confidence = min(confidence, 1.0)
            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    confidence=round(confidence, 2),
                    detector=self.__class__.__name__,
                )
            )
        return found
