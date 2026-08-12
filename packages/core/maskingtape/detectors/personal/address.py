"""주소 탐지기 — 시/도명을 기준으로 지번·도로명 주소 패턴을 찾는다.

동작 원리:
1. 시/도명(사전 기반, 신구 행정명 모두 포함)이 나오면 후보로 삼는다.
2. 뒤에 시/군/구(2단계까지), 읍/면/동/리 또는 도로명, 번지(건물번호), 건물명+동/호가
   순서대로 이어지는지 확인하고 이어지는 만큼 구간을 넓힌다.
3. 매칭된 구성 요소가 많을수록(시/도만 vs 동/번지/건물까지 전부) 확신도를 높인다.
   "서울특별시청"처럼 시/도명이 다른 단어의 일부일 뿐이면 매칭하지 않는다.
4. 시/도 없이 시/군으로 시작하는 주소("성남시 분당구 정자동 45-6")도 별도 앵커로 잡는다.
   시/군 뒤에 구·동/읍/면/리가 이어질 때만(지역 언급·조사 배제) 낮은 확신도(0.4~)로 잡는다(이슈 #68).

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

# 시/도 앵커와 시/군 앵커가 공유하는 꼬리. 시/군/구·동·번지·건물을 이어붙인다.
# 시/군/구는 두 단계까지 이어진다 — "성남시 분당구", "수원시 영통구".
_GU = r"(?:\s(?P<gu>[가-힣]{1,10}[시군구]))?"
_GU2 = r"(?:\s(?P<gu2>[가-힣]{1,10}[군구]))?"
_TAIL = (
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

# 시/도명 뒤에 공백 없이 붙는 조사(에/로/의/은/는/이/가/에서/으로/까지 …)는 정상 한국어 표기라
# 시/도만으로도 주소로 인정해야 한다("본사는 서울특별시에 있다" → 주소 '서울특별시'). 반면 조사가
# 아닌 한글이 붙으면 다른 단어의 일부다("서울특별시청"의 '청") — 이건 제외한다(#196).
# 계사(이다)의 활용형("주소는 X입니다/예요/였…")도 자기 주소를 설명하는 흔한 표기라 허용한다(#248).
# 이-로 시작하는 활용형(이다·이에요·이라·이었…)은 아래 '이'가 이미 커버한다.
# 긴 조사(에서·으로·까지·입니다)부터 둬야 "에서"가 "에"로 잘리지 않는다.
_JOSA = "입니다|입니까|예요|였|에서|에게|으로|까지|부터|처럼|보다|조차|마저|밖에|마다|한테|의|에|로|은|는|이|가|을|를|과|와|도|만"

_ADDR_RE = re.compile(
    # 시/도명 뒤: '조사가 아닌 한글'이 공백 없이 붙으면 다른 단어의 일부이므로 제외(#196).
    # 조사(…시에/…시로/…시에서)나 비한글(공백·문장부호·끝)이 오면 시/도만으로도 주소로 인정한다.
    # gu/dong/bunji 뒤에 조사가 붙는 건 원래도 허용된다("...123-4에 거주").
    r"(?P<province>" + _PROVINCE_RE + r")(?!(?!" + _JOSA + r")[가-힣])" + _GU + _GU2 + _TAIL
)

# 시/도 없이 시/군으로 시작하는 주소 — "성남시 분당구 정자동 45-6"(#68).
# 시/도 사전을 시작점으로 삼는 _ADDR_RE는 이런 표기를 통째로 놓쳐 유출된다.
_ADDR_NO_PROVINCE_RE = re.compile(
    # 앞에 한글이 붙으면 다른 단어의 일부이므로 시작점으로 보지 않는다.
    r"(?<![가-힣])(?P<si>[가-힣]{2,9}[시군])"
    # 오탐 억제: 시/군 바로 뒤에 구 또는 동/읍/면/리가 와야만 주소 후보로 인정한다.
    # "성남시로 이사"의 조사 '로'(공백 없음)와 "강남구에서"의 구 단독을 배제한다.
    r"(?=\s[가-힣]{1,10}(?:구|동|읍|면|리))" + _GU + _GU2 + _TAIL
)


def _score(m: re.Match[str], base: float, cap: float) -> float:
    """매칭된 구성 요소가 많을수록 확신도를 높인다(시/군만 vs 동·번지·건물까지)."""
    confidence = base
    if m.group("gu"):
        confidence += 0.15
    if m.groupdict().get("gu2"):
        confidence += 0.05
    if m.group("dong"):
        confidence += 0.15
    if m.group("bunji"):
        confidence += 0.2
    if m.group("building"):
        confidence += 0.15
    return round(min(confidence, cap), 2)


class AddressDetector(Detector):
    """한국 행정구역 주소 탐지기 (시/도 단위부터 번지까지)."""

    kind = "address"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        province_spans: list[tuple[int, int]] = []
        # 시/도 앵커 — 확신도 0.5부터 시작.
        for m in _ADDR_RE.finditer(text):
            province_spans.append((m.start(), m.end()))
            found.append(self._make(m, base=0.5, cap=1.0))
        # 시/군 앵커(시/도 없음) — 확신도 0.4부터. 시/도가 없어 확신이 낮으니 임계값으로 조절 가능.
        for m in _ADDR_NO_PROVINCE_RE.finditer(text):
            if not m.group("dong"):
                continue  # 동/읍/면/리(도로명 포함) 없이 시/군+구만이면 지역 언급일 뿐 — 유출 아님
            if any(m.start() < end and m.end() > start for start, end in province_spans):
                continue  # 시/도 앵커 매칭에 이미 포함된 구간이므로 중복
            found.append(self._make(m, base=0.4, cap=0.9))
        found.sort(key=lambda d: d.start)
        return found

    def _make(self, m: re.Match[str], base: float, cap: float) -> Detection:
        return Detection(
            kind=self.kind,
            start=m.start(),
            end=m.end(),
            text=m.group(0),
            confidence=_score(m, base, cap),
            detector=self.__class__.__name__,
        )
