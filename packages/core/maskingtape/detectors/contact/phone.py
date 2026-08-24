# SPDX-License-Identifier: Apache-2.0

"""전화번호 탐지기 — 휴대폰·유선·인터넷 전화(070)·평생번호(050X) 번호를 찾는다.

동작 원리:
1. 휴대폰: 01X(010/011/016/017/018/019) 계열을 정규식으로 찾는다. +82 국가번호 표기 허용.
2. 유선·특수: 지역번호(02, 031~033, 041~044, 051~055, 061~064), 인터넷 전화 070,
   평생번호·안심번호 050X(050/0502~0508). 050X는 실번호를 숨기는 개인 연락처라 개인정보다.
3. 구분자(-, ., 공백)가 있으면 확신도를 높게, 숫자만 붙어 있으면 낮게 준다.
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 그룹 사이 구분자 — 하이픈/점/공백에 더해 en-dash·em-dash와 "공백-하이픈-공백"·이중공백
# 조합도 허용한다(Word·HWP 자동서식·표 붙여넣기에서 흔함). 상한 {0,3}이라 ReDoS 없음.
# 이게 없으면 "010 - 1234 - 5678"에서 전화번호가 통째로 샌다(미탐=유출).
_SEP = r"[-.\s–—]{0,3}"

# 휴대폰 — +82 표기 시 앞자리 0 생략 허용 (+82 10-XXXX-XXXX)
_MOBILE_RE = re.compile(r"(?<!\d)(?:\+82[-.\s]?0?|0)1[016789]" + _SEP + r"\d{3,4}" + _SEP + r"\d{4}(?!\d)")

# 유선·특수 — 서울 02, 광역 지역번호 3자리, 인터넷 전화 070, 평생번호·안심번호 050X.
# 050\d?는 050(3자리)과 0502~0508(4자리)을 함께 잡는다.
_LANDLINE_RE = re.compile(
    r"(?<!\d)0(?:2|3[1-3]|4[1-4]|5[1-5]|6[1-4]|70|50\d?)" + _SEP + r"\d{3,4}" + _SEP + r"\d{4}(?!\d)"
)


def _has_separator(matched: str) -> bool:
    return any(sep in matched for sep in ("-", ".", " "))


class PhoneDetector(Detector):
    """한국 전화번호 탐지기."""

    kind = "phone"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        # (정규식, 구분자 있을 때 확신도, 숫자만 붙어 있을 때 확신도)
        for regex, with_sep, bare in ((_MOBILE_RE, 1.0, 0.9), (_LANDLINE_RE, 0.95, 0.8)):
            for m in regex.finditer(text):
                found.append(
                    Detection(
                        kind=self.kind,
                        start=m.start(),
                        end=m.end(),
                        text=m.group(0),
                        confidence=with_sep if _has_separator(m.group(0)) else bare,
                        detector=self.__class__.__name__,
                    )
                )
        return found
