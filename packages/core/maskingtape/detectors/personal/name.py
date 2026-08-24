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

# 이름 뒤에 자주 오는 직함. 후보 판정 + 규칙 매칭의 suffix 단서로 쓴다(#213).
# 업무·계약 문서는 "홍길동 대표"처럼 직함이 이름과 존칭 사이에 끼어, 존칭만 보던 예전 규칙은
# 이름을 통째로 놓쳤다. 직함 단서 하나만 있으면 확신도 0.5라 하이브리드판의
# NameDetector(min_confidence=0.75) 안전망엔 안 섞이고, 규칙 전용(더 가리기=안전) 경로에서만
# 추가로 잡힌다 — 정밀도 크리티컬한 하이브리드 경로엔 영향이 없다.
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
# "이사"는 "대표이사"가 띄어쓰기돼("대표 이사가") 이름으로 오탐되던 걸 막는다(#239).
_NON_NAME_WORDS = (
    "전화번호", "이메일", "주민등록번호", "주민번호", "주민등록증",
    "주소", "나이", "성별", "생년월일", "이용", "이유", "이사",
)

# 직함 전용 단서(존칭 '님' 제외). 이것만으로(다른 단서 없이) 이름을 잡을 땐 성+2자 풀네임을
# 요구한다 — 부서·업무어("구매 부장"의 구매, "대표 이사"의 이사)가 직함과 붙어 이름으로
# 오탐되는 걸 막는다. 존칭(님)은 강한 단서라 이 제약을 걸지 않는다. (앞·뒤 직함 공용)
_TITLE_ONLY_CUES = frozenset(_TITLE_CUES) - frozenset(_SUFFIX_CUES)

# 직함만 단서일 때 걸러낼 2자 부서·업무어 — 성씨로 시작해 이름처럼 보인다. 뒤에 조사가 붙어
# 3자로 보여도(#247, "정기가"=정기+가) stem으로 걸러낸다. 완전한 목록은 아니고(긴 꼬리는 LLM
# 담당) 흔한 것만 둔다. 실명은 조사로 끝나도 stem이 여기 없으면 그대로 잡혀 유출되지 않는다.
_DEPT_STEMS = frozenset({"구매", "정기", "홍보", "안전", "노무"})
# 이름 뒤에 붙는 단일 음절 조사 — 부서어 뒤에 붙어 3글자 가드를 우회하는지 판별에만 쓴다(#247).
_JOSA_CHARS = frozenset("이가은는을를도만의에로과와")

_SURNAME_ALT = "|".join(sorted(_SURNAMES, key=len, reverse=True))
# 이름 앞 단서 = 역할어 + 직함. 직함이 이름 앞에 오는 형태("대표 홍길동")도 잡는다(#239).
_PREFIX_ALT = "|".join(
    sorted(dict.fromkeys(_PREFIX_CUES + sorted(_TITLE_ONLY_CUES)), key=len, reverse=True)
)
# 이름 뒤 단서 = 존칭·역할어 + 직함. 직함도 규칙 매칭 단서로 편입한다(#213). "님"은 양쪽에
# 있으므로 dict.fromkeys로 중복을 없앤 뒤 긴 것부터 매칭한다.
_SUFFIX_ALT = "|".join(sorted(dict.fromkeys(_SUFFIX_CUES + _TITLE_CUES), key=len, reverse=True))

# 이름의 2번째 글자로 삼키면 안 되는 단일 존칭 — 뒤 suffix 그룹이 잡도록 양보한다(#147).
# 탐욕적 매칭이 "고객 심진님"의 "심진님"을 통째로 삼켜 gold("심진")와 어긋나던 문제.
# 님·씨만 둔다: 이 둘은 이름 음절로 거의 안 쓰인다. 반면 군·양은 실명 끝음절로 흔해서
# ("김하양"·"박도군") 여기 넣으면 그 글자를 이름에서 떼어내 유출된다(#340) — 미탐=유출이라
# 이름에 포함(더 가리기=안전). "홍길 군"처럼 공백이 있으면 어차피 suffix 그룹이 잡는다.
# 조사(이·가·은 등)는 이름 글자와 겹쳐(재이·지은·박도) 규칙으로 뺄 수 없어 제외 — LLM판이 처리.
_HONORIFIC_TAIL = "님씨"

_NAME_RE = re.compile(
    r"(?:(?P<prefix>" + _PREFIX_ALT + r")[:\s]{1,2})?"
    # 성씨는 단어(어절) 시작이어야 한다 — 앞에 한글이 붙어 있으면 단어 중간이라 이름이 아니다(#158).
    # 이게 없으면 "감지되어"의 "지"(성씨 사전)부터 "지되어"가 이름으로 잡히고, 뒤 "양빈도"의 "양"을
    # 존칭으로 삼켜 오탐이 된다. 앞이 공백/문장부호/문두면 통과하므로 정상 이름은 그대로 잡힌다.
    r"(?<![가-힣])"
    # 성씨 + 1글자, 2번째 글자는 단일 존칭이 아닐 때만 붙인다(#147) — 존칭은 suffix 그룹이 잡는다.
    r"(?P<name>(?:" + _SURNAME_ALT + r")[가-힣](?:(?![" + _HONORIFIC_TAIL + r"])[가-힣])?)"
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

            prefix = m.group("prefix")
            suffix = m.group("suffix")
            has_prefix = prefix is not None
            has_suffix = suffix is not None
            if not has_prefix and not has_suffix:
                continue  # 문맥 단서가 하나도 없으면 일반 단어와 구분 못 하므로 버린다

            # 직함 하나만 단서일 땐(앞이든 뒤든) 성+2자 풀네임(3글자)만 인정 — 부서·업무어가
            # 직함에 붙어 이름으로 오탐되는 걸 막는다(#213 뒤 직함, #239 앞 직함).
            title_only = (suffix in _TITLE_ONLY_CUES and not has_prefix) or (
                prefix in _TITLE_ONLY_CUES and not has_suffix
            )
            if title_only:
                name = m.group("name")
                # 부서·업무어(2자) 뒤에 조사가 붙어 3자로 보이는 경우("정기가"=정기+가)도 버린다(#247).
                # 실명이 우연히 조사로 끝나면(김지은) stem이 부서어가 아니라 그대로 잡힌다.
                if len(name) < 3 or (
                    len(name) == 3 and name[-1] in _JOSA_CHARS and name[:2] in _DEPT_STEMS
                ):
                    continue

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
