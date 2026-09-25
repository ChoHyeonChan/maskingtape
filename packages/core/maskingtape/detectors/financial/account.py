# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""계좌번호 탐지기 — 문맥(계좌 관련어·은행 이름) 필수 + 숫자 그룹 패턴.

동작 원리:
1. 한국 계좌번호는 **체크섬이 없고 은행별 형식이 제각각**(2~4개 하이픈 그룹, 총 10~14자리)이라,
   형식만으로 잡으면 주문번호·일련번호 같은 무관한 숫자열을 오탐한다.
2. 그래서 번호 근처에 아래 셋 중 하나가 있을 때만 탐지한다 — 문맥이 없으면 버린다.
   (사업자등록번호 교훈: 체크섬이 없으면 문맥 + 측정.)
   - "은행"·"뱅크"나 계좌 관련어("계좌","입금","이체"…)가 앞뒤 15자 안에 있다 (_ALL_CUES)
   - 다른 낱말과 헷갈리지 않는 은행 이름("신한","농협","관악신협","새마을금고"…)이 앞뒤 15자 안에
     있다 (_BANK_NAMES_NEARBY·_BANK_NAMES_LOCAL·_BANK_NAMES_LONG, #472)
   - 일상어와 겹치는 은행 이름("우리","하나","국민"…)이 번호 **바로 앞**이나 번호 뒤 괄호 안에
     있다 (_BANK_NAMES_ADJACENT, #472). "우리 가게 주문번호 …"처럼 떨어져 있으면 문맥이 아니다.
3. 체크섬이 없어 확신도는 0.6으로 낮춘다.

보안: 계좌번호 누락은 금융정보 유출이다. 그래서 문맥이 있을 때는 놓치지 않도록 하이픈 그룹과
붙여 쓴 숫자를 모두 잡되, 반복에 상한을 둬 ReDoS를 막는다(모든 수량자가 유한 범위).
은행 이름을 문맥으로 더 받아도 가리는 범위는 넓어지기만 한다. 파이프라인이 겹친 탐지를
합집합으로 합치기 때문이다(pipeline._resolve_overlaps).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 하이픈으로 나뉜 그룹 2~4개 또는 붙여 쓴 10~14자리. 7자리 그룹은 카카오뱅크식
# "3333-01-1234567"의 마지막 묶음까지 담기 위함이다. 앞뒤가 숫자/하이픈이면 더 긴 번호의
# 일부이므로 경계로 제외한다. 총 자릿수(10~14) 검증은 detect에서 한다.
# 그룹은 2~7자리인데, **마지막 그룹만** 한 자리도 받는다(#472). 새마을금고(9002-1234-5678-1,
# 4-4-4-1)와 옛 신협(12345-67-12345-1, 5-2-5-1)은 끝에 검증 숫자 한 자리를 따로 떼어 쓴다.
# 이 식은 예전 식(모든 그룹 2~7자리)이 받던 모양을 전부 받는다. 게다가 앞뒤 경계 때문에 매치는
# 늘 숫자·하이픈 덩어리 전체라서, 예전에 잡던 번호를 새 식이 다르게 잘라 놓치는 일도 없다.
_ACCOUNT_RE = re.compile(r"(?<![\d-])(?:\d{2,7}(?:-\d{2,7}){0,2}-\d{1,7}|\d{10,14})(?![\d-])")

# 문맥어 — 하나라도 매치 근처에 있어야 계좌로 본다.
# "은행"·"뱅크"(어느 은행이든 이 접미어가 붙는다) + 계좌 행위어다. 이 단어들은 무관한 단어의
# 부분열로 잘 끼지 않아서 창 안에 있기만 하면 인정한다. 은행 이름은 아래 두 목록이 따로 맡는다.
_ALL_CUES = (
    "계좌", "입금", "이체", "예금주", "예금", "출금", "송금", "은행", "뱅크",
)

# 문맥어를 찾는 창(문자 수) — 매치 앞뒤로 이만큼 본다. "국민은행 123-…"(앞)과 "123-… 로 입금"(뒤) 모두 커버.
_CUE_WINDOW = 15

# 은행 이름만 붙여 쓴 표기("신한 110-123-456789")가 흔한데, 위 문맥어만으로는 놓쳤다(#472).
# 은행 이름은 다른 낱말과 헷갈리는 정도가 달라서 두 목록으로 나눈다.
#
# 1) 다른 낱말과 헷갈리지 않는 이름 — 창(앞뒤 15자) 안에만 있으면 문맥으로 본다.
#    "신한 홍길동 110-…"처럼 이름과 번호 사이에 예금주가 끼는 표기도 잡기 위해서다.
#    이름 앞 글자가 한글이면 다른 낱말의 일부로 보고 받지 않는다("혁신협의회"의 "신협",
#    "특수협약"의 "수협", "갱신한"의 "신한").
_BANK_NAMES_NEARBY = ("신한", "카뱅", "케뱅", "SC제일")
# 1-1) 지역 이름을 앞에 붙여 쓰는 상호금융("안성농협", "관악신협", "제주수협") — 위 규칙에 더해,
#      앞 글자가 한글이어도 이름 바로 뒤가 낱말 끝(한글이 아닌 글자)이면 받는다. 그래야
#      "영농협동"·"혁신협의회"·"건축협회"처럼 낱말 한가운데 든 것은 계속 거른다.
_BANK_NAMES_LOCAL = ("농협", "축협", "수협", "신협")
# 1-2) 다른 낱말 안에 들어갈 일이 없는 긴 이름 — 앞뒤 글자와 상관없이 받는다
#      ("화곡새마을금고에서", "양평산림조합으로").
_BANK_NAMES_LONG = ("새마을금고", "산림조합")
# "신"은 '새(新)'라는 접두어이기도 해서 "신협약"·"신협정"·"신한류"·"신한일" 같은 낱말을 만든다.
# 이름 바로 뒤에 이 글자가 오면 은행 이름이 아니다.
_NOT_BANK_AFTER = {
    "신한": ("국", "류", "옥", "일"),
    "신협": ("약", "정", "력", "상", "업", "의체"),
}
# 창 오른쪽 끝에 걸린 이름도 뒤 글자를 보고 판단하도록, 찾을 때만 창을 이만큼 더 넓힌다.
# 이름 자체는 여전히 창 안에서 끝나야 한다(_has_bank_name_cue).
_LOOKAHEAD_SLACK = max(len(s) for tails in _NOT_BANK_AFTER.values() for s in tails)

# 2) 일상어와 겹치는 이름 — 번호 **바로 앞**(공백·쌍점·괄호·빗금·하이픈 4자 이내)이거나 번호 뒤
#    괄호 안일 때만 문맥으로 본다. 창 안에 있기만 해도 받으면 계좌가 아닌 번호를 가린다. #472에서
#    재 보니 "우리 가게 주문번호 2026-0925-1234", "하나 더 보냈어요 송장번호 …", "국민 여러분
#    민원번호 …"처럼 5개 중 4개가 오탐이었다. 우체국(택배 운송장), 토스·카카오(결제 주문번호),
#    지역 이름(부산·대구…)도 계좌가 아닌 번호 옆에 흔해서 여기 둔다. 다만 번호 바로 앞에 붙은
#    "우체국 6012345678901"(운송장)은 계좌와 모양이 같아 구분할 수 없어 가린다. 더 가리는 쪽이 안전하다.
_BANK_NAMES_ADJACENT = (
    "우리", "하나", "국민", "기업", "산업", "씨티", "우체국", "토스", "카카오", "새마을",
    "부산", "경남", "광주", "전북", "제주", "대구",
)
_BANK_NAMES_ADJACENT_LATIN = ("KB", "NH", "IBK", "KDB")


def _alternation(names: tuple[str, ...]) -> str:
    """이름들을 정규식 선택지(a|b|…)로 묶는다.

    긴 이름부터 둬서, 한 이름이 다른 이름의 앞부분이어도 긴 쪽이 먼저 맞게 한다.
    _NOT_BANK_AFTER에 있는 이름은 그 글자가 뒤따르지 않을 때만 맞는다.
    """
    parts = []
    for name in sorted(names, key=len, reverse=True):
        part = re.escape(name)
        if name in _NOT_BANK_AFTER:
            part += "(?!" + "|".join(_NOT_BANK_AFTER[name]) + ")"
        parts.append(part)
    return "|".join(parts)


# 한글 이름은 앞 글자가 한글이 아닐 때만 받는다(위 1·2번의 낱말 일부 거르기, "하나하나"의 뒤
# "하나"도 여기서 걸러진다). "NH농협", "KB국민"처럼 영문 약칭이 앞에 붙는 표기는 그대로 받는다.
# 영문 이름은 앞이 영문·숫자가 아닐 때만 받는다("512KB"의 "KB"는 은행이 아니다).
_BANK_NEARBY_RE = re.compile(
    r"(?<![가-힣])(?:" + _alternation(_BANK_NAMES_NEARBY + _BANK_NAMES_LOCAL) + r")"
    r"|(?<=[가-힣])(?:" + _alternation(_BANK_NAMES_LOCAL) + r")(?![가-힣])"
    r"|(?:" + _alternation(_BANK_NAMES_LONG) + r")"
)
_BANK_ADJACENT = (
    r"(?:(?<![가-힣])(?:" + _alternation(_BANK_NAMES_ADJACENT) + r")"
    r"|(?<![A-Za-z0-9])(?:" + _alternation(_BANK_NAMES_ADJACENT_LATIN) + r"))"
)
# 번호 바로 앞: 이름 뒤에 공백(줄 안 공백·NBSP)·쌍점·괄호·빗금·하이픈이 4자까지 오고 곧바로 번호가
# 시작한다("우리 1002-…", "우리: 1002-…", "국민 - 123456-…", "우리/1002-…"). 줄바꿈은 받지 않는다
# ("하나\n6123-…"는 목록의 한 줄일 뿐이다). 끝 표시는 $가 아니라 \Z다. $는 끝의 줄바꿈 앞에서도
# 맞아서 줄바꿈을 건너뛰게 된다.
_BANK_BEFORE_RE = re.compile(_BANK_ADJACENT + r"[ \t :：()\[\]/-]{0,4}\Z")
# 번호 뒤 괄호 안: "1002-123-456789 (우리)". 괄호 없이 뒤에 오는 이름은 받지 않는다
# ("주문번호 2026-0925-1234 하나 더 주세요"). 공백은 자리마다 3자까지만 본다(반복 상한).
_BANK_AFTER_RE = re.compile(
    r"[ \t ]{0,3}[(\[][ \t ]{0,3}" + _BANK_ADJACENT + r"[ \t ]{0,3}[)\]]"
)
# 번호 앞에서 이름을 찾을 때 거슬러 볼 글자 수 — 가장 긴 이름 + 사이 글자 4자
_BANK_BEFORE_REACH = max(map(len, _BANK_NAMES_ADJACENT + _BANK_NAMES_ADJACENT_LATIN)) + 4


def _has_bank_name_cue(text: str, start: int, end: int) -> bool:
    """번호 text[start:end] 근처에 은행 이름이 문맥으로 있는지 본다(#472).

    정해진 창만 훑는다. 뒤보기((?<!…))는 pos 앞 글자도 보므로, 창 왼쪽 끝에 걸친 "혁|신협"도
    낱말 일부로 제대로 거른다. 오른쪽은 _LOOKAHEAD_SLACK만큼 더 읽어 "신협|약"처럼 창 끝에
    걸린 이름도 뒤 글자를 보고 거르되, 이름 자체는 창 안에서 끝나야 받는다. 모든 식의 반복에
    상한이 있고 창 크기가 고정이라, 번호 하나당 드는 일이 번호 길이와 창 크기로 정해진다.
    """
    limit = end + _CUE_WINDOW
    for m in _BANK_NEARBY_RE.finditer(text, max(0, start - _CUE_WINDOW), limit + _LOOKAHEAD_SLACK):
        if m.end() <= limit:
            return True
    if _BANK_BEFORE_RE.search(text, max(0, start - _BANK_BEFORE_REACH), start):
        return True
    return _BANK_AFTER_RE.match(text, end) is not None


class AccountDetector(Detector):
    """계좌번호 탐지기 (문맥어 기반, 체크섬 없음)."""

    kind = "account"

    def detect(self, text: str) -> list[Detection]:
        """자릿수(10~14)와 문맥을 둘 다 확인한 후보만 확신도 0.6으로 돌려준다.

        계좌번호는 체크섬이 없어 형식만으로는 주문번호 같은 숫자열과 구분되지 않는다.
        그래서 후보 앞뒤 _CUE_WINDOW(15자) 안에 _ALL_CUES('은행'·'뱅크'나 '계좌'·'입금' 같은
        계좌 관련어)가 있거나, 은행 이름이 문맥으로 있어야 한다(_has_bank_name_cue).
        '우리'·'하나' 같은 일상어 은행 이름은 번호 바로 앞에 붙을 때만 문맥으로 본다.
        """
        found: list[Detection] = []
        for m in _ACCOUNT_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if not (10 <= len(digits) <= 14):
                continue  # 한국 계좌번호 자릿수 범위 밖은 계좌가 아니다

            left = max(0, m.start() - _CUE_WINDOW)
            context = text[left : m.end() + _CUE_WINDOW]
            if not any(cue in context for cue in _ALL_CUES) and not _has_bank_name_cue(
                text, m.start(), m.end()
            ):
                continue  # 계좌 관련어도 은행 이름도 없으면 그냥 숫자열이므로 버린다

            found.append(
                Detection(
                    kind=self.kind,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    confidence=0.6,
                    detector=self.__class__.__name__,
                )
            )
        return found
