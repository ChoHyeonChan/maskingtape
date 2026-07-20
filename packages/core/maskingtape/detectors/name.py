"""이름 탐지기 — 성씨 사전 + 문맥 단서 기반 임시 규칙판(Ollama+Qwen 로컬 LLM 버전 나오기 전까지).

동작 원리:
1. 흔한 한글 성씨(사전) 뒤에 1~2글자 이름이 붙은 자리를 후보로 삼는다.
2. 성씨+이름만으로는 그냥 일반 단어와 구분이 안 되므로("이용", "김치" 등), 앞에 역할어
   ("고객", "환자", "작성자" 등)나 뒤에 존칭("님", "씨" 등)이 붙어 있을 때만 탐지한다 — 둘 다 없으면 버린다.
3. 앞뒤 문맥 단서가 둘 다 있으면 확신도를 높게(0.75), 하나만 있으면 낮게(0.5) 준다.

한계(의도된 트레이드오프): 문맥 단서 단어가 성씨와 무관하게 등장해도 매칭될 수 있어
("고객 이용 안내"의 "이용"이 성씨 "이"+이름 "용"으로 오탐될 수 있음) 정밀도가 다른 규칙
탐지기보다 낮다. 문맥을 실제로 이해하는 로컬 LLM(Ollama+Qwen) 버전으로 교체하기 전까지의
임시 버전임을 감안한다.
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 인구 비중이 높은 한글 성씨(한 글자) — 필요시 확장.
_SURNAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
    "노", "하", "곽", "성", "차", "주", "우", "구", "민", "나",
    "진", "지", "엄", "채", "원", "천", "방", "공", "현", "함",
]

# 이름 앞에 오는 역할어 — 뒤에 공백/콜론이 붙어 이름으로 이어진다.
_PREFIX_CUES = ["고객", "환자", "신청자", "작성자", "담당자", "수령인", "수신인", "성명", "이름", "저는"]

# 이름 뒤에 오는 존칭·역할어 — 공백 없이 붙거나(님께) 공백을 두고(환자분) 이어질 수 있다.
_SUFFIX_CUES = [
    "선생님", "고객님", "환자분",
    "님", "씨", "군", "양",
    "담당자", "작성자", "신청자", "수령인", "수신인",
]

# 성씨로 시작하지만 실제로는 이 도메인(개인정보 서식)에서 라벨로 흔히 쓰이는 일반 단어 —
# "고객 전화번호", "성명 및 주소" 처럼 역할어 바로 뒤에 붙어 나오면 이름으로 오탐하기 쉽다.
_NON_NAME_WORDS = (
    "전화번호", "이메일", "주민등록번호", "주민번호", "주민등록증",
    "주소", "나이", "성별", "생년월일", "이용", "이유",
)

_SURNAME_ALT = "|".join(sorted(_SURNAMES, key=len, reverse=True))
_PREFIX_ALT = "|".join(sorted(_PREFIX_CUES, key=len, reverse=True))
_SUFFIX_ALT = "|".join(sorted(_SUFFIX_CUES, key=len, reverse=True))

_NAME_RE = re.compile(
    r"(?:(?P<prefix>" + _PREFIX_ALT + r")[:\s]{1,2})?"
    r"(?P<name>(?:" + _SURNAME_ALT + r")[가-힣]{1,2})"
    r"(?:\s?(?P<suffix>" + _SUFFIX_ALT + r"))?"
)


class NameDetector(Detector):
    """성씨+문맥 단서 기반 임시 이름 탐지기 (로컬 LLM 버전 나오기 전까지)."""

    kind = "name"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _NAME_RE.finditer(text):
            if any(text.startswith(word, m.start("name")) for word in _NON_NAME_WORDS):
                continue  # "주민번호"처럼 성씨로 시작하는 도메인 라벨 단어는 이름이 아니다

            has_prefix = m.group("prefix") is not None
            has_suffix = m.group("suffix") is not None
            if not has_prefix and not has_suffix:
                continue  # 문맥 단서가 하나도 없으면 일반 단어와 구분 못 하므로 버린다

            confidence = 0.75 if (has_prefix and has_suffix) else 0.5
            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start("name"),
                    end=m.end("name"),
                    text=m.group("name"),
                    confidence=confidence,
                    detector=self.__class__.__name__,
                )
            )
        return found
