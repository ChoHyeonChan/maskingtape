"""운전면허번호 탐지기 — 정규식(지역명 + 형식) + 문맥어.

동작 원리:
1. "지역명-연도(2자리)-일련번호(6자리)-검증번호(2자리)" 형식을 정규식으로 찾는다.
   구분자는 하이픈/공백을 섞어 써도 된다("서울-99 123456-78"도 매치).
2. 지역명을 16개 시/도 이름 중 하나로 고정한다 — 지역명이 없으면 그냥 숫자 나열이라
   전화번호·사업자등록번호 등과 구분이 안 돼 오탐이 늘어난다.
3. 검증번호(마지막 2자리)의 실제 체크섬 알고리즘은 공개돼 있지 않아 계산하지 않는다
   (여권번호와 같은 한계) — 그래서 문맥어("운전면허"/"면허")가 가까이 있으면 확신도를
   높이고(0.9), 형식만이면 낮게(0.6) 준다. 낮아도 마스킹은 되므로(과탐=안전) 임계값으로
   조절할 수 있다.

운전면허번호는 개인정보보호법상 고유식별정보다(identity/ 도메인).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 16개 시/도 지역명 — 이슈에 명시된 목록 그대로("등"으로 더 있을 수 있음이 언급됐지만
# 구체적으로 나열되지 않은 지역은 여기 포함하지 않는다).
_REGIONS = (
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
)
_REGION_GROUP = "|".join(_REGIONS)

# 구분자는 하이픈 또는 공백(혼용 가능).
_SEP = r"[-\s]"

# 지역명 + 연도(2) + 일련번호(6) + 검증번호(2). 지역명 앞이 한글이면(다른 단어 중간에서
# 우연히 시작한 것일 수 있어) 제외하고, 뒤에 숫자가 더 붙으면(더 긴 숫자열의 일부) 제외한다.
_DRIVER_LICENSE_RE = re.compile(
    rf"(?<![가-힣])(?:{_REGION_GROUP}){_SEP}(\d{{2}}){_SEP}(\d{{6}}){_SEP}(\d{{2}})(?!\d)"
)

# 문맥어가 앞쪽 이 글자수 안에 있으면 운전면허번호일 확신이 높다.
_CONTEXT_WINDOW = 15


class DriverLicenseDetector(Detector):
    """대한민국 운전면허번호 탐지기 (지역명 + 형식, 체크섬 없음)."""

    kind = "driver_license"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _DRIVER_LICENSE_RE.finditer(text):
            context = text[max(0, m.start() - _CONTEXT_WINDOW) : m.start()]
            confidence = 0.9 if "면허" in context else 0.6
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
