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

# 인구 비중이 높은 한글 성씨. 상위 50개면 인구의 99% 이상을 덮는다 — 나머지 200여 개를
# 다 넣기보다 흔한 것 + 흔한 복성(두 글자)만 둔다. 못 덮는 희귀 성씨는 문맥 단서로 건진다.
_SURNAMES = [
    # 복성(두 글자) — 정규식에서 긴 것부터 매칭돼야 "선우예진"을 선+우예진이 아닌 선우+예진으로 본다
    "남궁", "선우", "제갈", "황보", "독고", "서문", "사공",
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
    "노", "하", "곽", "성", "차", "주", "우", "구", "민", "나",
    "진", "지", "엄", "채", "원", "천", "방", "공", "현", "함",
]

# 이름 뒤에 자주 오는 직함 — 후보 판정에만 쓴다(규칙 매칭에는 오탐 위험이 있어 넣지 않는다).
# 희귀 성씨("남궁민수 팀장")를 성씨 사전 없이 문맥으로 건지는 안전망.
_TITLE_CUES = [
    "팀장", "과장", "부장", "차장", "대리", "사원", "실장", "본부장",
    "이사", "대표", "원장", "교수", "주임", "반장", "사장", "회장", "님",
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

# 후보 판정용: 성씨(복성 포함)로 시작해 한글이 이어지는 자리
_CANDIDATE_RE = re.compile(r"(?:" + _SURNAME_ALT + r")[가-힣]")

# 후보 판정에 쓰는 문맥 단서 전체 (역할어 + 존칭 + 직함)
_ALL_CUES = tuple(dict.fromkeys(_PREFIX_CUES + _SUFFIX_CUES + _TITLE_CUES))


def has_name_candidate(text: str) -> bool:
    """이 텍스트에 사람 이름이 있을 가능성이 있는지 — LLM에 보낼지 정하는 느슨한 필터.

    성씨(복성 포함) 뒤에 한글이 이어지거나, 역할어·존칭·직함 단서가 있으면 후보로 본다.
    **느슨하게** 잡는다: 놓치면 이름이 안 가려지므로(유출), 애매하면 후보로 넘긴다.
    후보가 하나도 없는 텍스트(순수 숫자·코드 등)만 걸러 LLM 호출을 아낀다.
    """
    if any(cue in text for cue in _ALL_CUES):
        return True
    # 성씨로 시작하는 후보가 도메인 라벨 단어("이메일"의 이 등)가 아니면 후보로 본다
    return any(
        not any(text.startswith(word, m.start()) for word in _NON_NAME_WORDS)
        for m in _CANDIDATE_RE.finditer(text)
    )


class NameDetector(Detector):
    """성씨+문맥 단서 기반 임시 이름 탐지기 (로컬 LLM 버전 나오기 전까지)."""

    kind = "name"

    def __init__(self, min_confidence: float = 0.0) -> None:
        """min_confidence 이상인 탐지만 돌려준다.

        LLM판과 함께 안전망으로 쓸 때 0.75를 주면 앞뒤 문맥 단서가 **둘 다** 있는
        확실한 것만 남아, 이 탐지기의 약점인 오탐(0.5짜리)을 섞지 않고 보강할 수 있다.
        """
        self.min_confidence = min_confidence

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
            if confidence < self.min_confidence:
                continue
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
