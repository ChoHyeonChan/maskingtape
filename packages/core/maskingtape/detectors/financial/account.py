# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""계좌번호 탐지기 — 문맥(계좌 관련어·은행 이름) 필수 + 숫자 그룹 패턴.

동작 원리:
1. 한국 계좌번호는 **체크섬이 없고 은행별 형식이 제각각**(2~4개 묶음, 총 10~14자리)이라,
   형식만으로 잡으면 주문번호·일련번호 같은 무관한 숫자열을 오탐한다. 묶음은 보통 하이픈으로
   나누지만 공백이나 점으로 나눠 쓰기도 한다("1002 123 456789", "110.123.456789", #474).
2. 그래서 번호 근처에 아래 셋 중 하나가 있을 때만 탐지한다 — 문맥이 없으면 버린다.
   (사업자등록번호 교훈: 체크섬이 없으면 문맥 + 측정.)
   - "은행"·"뱅크"나 계좌 관련어("계좌","입금","이체"…)가 앞뒤 15자 안에 있다 (_ALL_CUES)
   - 다른 낱말과 헷갈리지 않는 은행 이름("신한","농협","관악신협","새마을금고"…)이 앞뒤 15자 안에
     있다 (_BANK_NAMES_NEARBY·_BANK_NAMES_LOCAL·_BANK_NAMES_LONG, #472)
   - 일상어와 겹치는 은행 이름("우리","하나","국민"…)이 번호 **바로 앞**이나 번호 뒤 괄호 안에
     있다 (_BANK_NAMES_ADJACENT, #472). "우리 가게 주문번호 …"처럼 떨어져 있으면 문맥이 아니다.
3. 체크섬이 없어 확신도는 0.6으로 낮춘다.

보안: 계좌번호 누락은 금융정보 유출이다. 그래서 문맥이 있을 때 덜 놓치도록 하이픈·공백·점 등으로
나눈 묶음과 붙여 쓴 숫자를 받는다. 정규식은 역추적이 폭발하지 않게 짰다(반복에 상한을 두거나, 역추적할
갈래가 없는 \d+만 쓴다). 공백·점 표기는 숫자 묶음을 한 번 훑어 찾아 선형 시간이다. 공백·점 표기는
하이픈 식과 따로 찾아 후보만 더하므로 하이픈 번호를 잡던 동작은 그대로다.
남는 한계: 한 번호 안에서 구분자가 섞인 표기("110 123-456789"), 쉼표로 나눈 번호(금액과 구분할 수
없다), 문맥어가 앞뒤 15자 밖에 있는 번호. 반대로 더 가리는 쪽의 한계도 있다. 계좌 문맥어 옆에 공백으로
쓴 금액 열("입금액 출금액 150000 230000")은 계좌로 가려지고, 서로 다른 번호를 공백 한 칸으로만 붙여
쓰면 계좌 후보가 둘을 이어 파이프라인이 종류 하나만 보고한다(가리는 범위는 그대로다).
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
    "통장",  # "통장 사본 110-123-456789"처럼 계좌 대신 쓰는 말(#474 검증에서 미탐 확인)
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
_BANK_BEFORE_RE = re.compile(_BANK_ADJACENT + r"[ \t\u00a0:：()\[\]/-]{0,4}\Z")
# 번호 뒤 괄호 안: "1002-123-456789 (우리)". 괄호 없이 뒤에 오는 이름은 받지 않는다
# ("주문번호 2026-0925-1234 하나 더 주세요"). 공백은 자리마다 3자까지만 본다(반복 상한).
_BANK_AFTER_RE = re.compile(
    r"[ \t\u00a0]{0,3}[(\[][ \t\u00a0]{0,3}" + _BANK_ADJACENT + r"[ \t\u00a0]{0,3}[)\]]"
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


def _has_account_context(text: str, start: int, end: int) -> bool:
    """번호 text[start:end] 근처에 계좌 문맥(계좌 관련어나 은행 이름)이 있는지 본다.

    하이픈 표기와 공백·점 표기가 같은 기준을 쓰도록 한곳에 둔다.
    """
    context = text[max(0, start - _CUE_WINDOW) : end + _CUE_WINDOW]
    return any(cue in context for cue in _ALL_CUES) or _has_bank_name_cue(text, start, end)


# 공백·점 등으로 묶음을 나눈 표기(#474). "입금 계좌 1002 123 456789"처럼 바로 옆에 문맥어가 있어도
# 하이픈 식(_ACCOUNT_RE)은 붙여 쓴 하이픈만 구분자로 받아서 통째로 놓쳤다.
#
# 이 경로는 정규식 하나로 덩어리를 찾지 않고, 숫자 묶음을 앞에서부터 한 번 훑으며 구분자로 이어진
# 사슬을 만든다(_separated_windows). 묶음 수에 상한을 둔 정규식은 상한을 넘는 줄("입금 1 2 3 4 5 6
# 1002 123 456789")에서 계좌를 끊어 먹었고, 상한을 없앤 정규식은 시작점마다 끝까지 다시 훑어 제곱
# 시간이 된다. 한 번 훑기는 길이 제한 없이 선형이다.
#
# 구분자로 받는 것: 공백류(공백·탭·NBSP·전각 공백) 1~3자, 점(앞뒤 공백 2자까지), 앞뒤를 띄운
# 하이픈("110 - 123 - 456789"). 받지 않는 것: 줄바꿈(다른 줄의 숫자), 쉼표(금액의 천 단위
# "1,234,567,890원"), 붙여 쓴 하이픈("110-123"은 하이픈 식의 몫이다).
_SPACE_CHARS = " \t" + chr(0xA0) + chr(0x3000)  # 공백·탭·NBSP·전각 공백
_FULLWIDTH_DOT = chr(0xFF0E)
_WS = "[" + re.escape(_SPACE_CHARS) + "]"
_DOTS = "[." + _FULLWIDTH_DOT + "]"
_SEPARATOR_RE = re.compile(
    _WS + "{1,3}|" + _WS + "{0,2}" + _DOTS + _WS + "{0,2}|" + _WS + "{1,2}-" + _WS + "{1,2}"
)
_MAX_SEPARATOR_LEN = 5  # 위 식이 받는 가장 긴 구분자. 이보다 긴 틈은 식을 돌려 보지 않는다.
_DIGIT_GROUP_RE = re.compile(r"\d+")
_MAX_GROUP_DIGITS = 7  # 계좌번호 한 묶음의 최대 자릿수(카카오뱅크식 끝 묶음 7자리)


def _separator_kind(gap: str) -> str | None:
    """묶음 사이 글자 gap이 구분자면 종류("dash"·"dot"·"space")를, 아니면 None을 돌려준다."""
    if len(gap) > _MAX_SEPARATOR_LEN or not _SEPARATOR_RE.fullmatch(gap):
        return None
    if "-" in gap:
        return "dash"
    if "." in gap or _FULLWIDTH_DOT in gap:
        return "dot"
    return "space"


def _looks_like_date_or_ip(text: str, window: list[tuple[int, int]], kind: str) -> bool:
    """창이 계좌번호가 아니라 날짜로 시작하거나 IPv4 주소 모양이면 True를 돌려준다.

    - 날짜: 앞 세 묶음이 4·2·2자리이고 연(1900~2099)·월(1~12)·일(1~31)로 읽힌다
      ("입금 일시 2026 09 28 14 30"). 계좌번호가 4-2-2로 시작하는 형식은 흔치 않다.
    - IPv4: 점으로 나뉜 묶음 4개가 모두 3자리 이하이고 0~255다("192.168.100.200").
    """
    nums = [text[s:e] for s, e in window]
    if len(nums) >= 3 and [len(n) for n in nums[:3]] == [4, 2, 2]:
        year, month, day = int(nums[0]), int(nums[1]), int(nums[2])
        if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
            return True
    return kind == "dot" and len(nums) == 4 and all(len(n) <= 3 and int(n) <= 255 for n in nums)


def _chain_windows(
    text: str, chain: list[tuple[int, int]], kinds: list[str]
) -> list[tuple[int, int]]:
    """사슬에서 계좌번호가 될 수 있는 창을 **전부** 돌려준다.

    창은 이어진 묶음 2~4개, 구분자 한 종류(섞이면 서로 다른 숫자), 끝이 아닌 묶음 2자리 이상(마지막만
    한 자리 허용 — 하이픈 식과 같은 규칙), 합쳐서 10~14자리다. 점이나 띄운 하이픈으로 나눈 창은 묶음이
    3개 이상이어야 한다. 점 표기 계좌는 "110.123.456789"처럼 3묶음이고, 2묶음은 대개 문장 끝 점이나
    소수점이다("입금 금액 150000. 2026 …", "…1234560. 010 1234 5678"에서 두 번호를 잇지 않게).
    한 창만 고르면 앞에 붙은 숫자부터 창이 잡힐 때 계좌 뒷부분이 남는다("입금 계좌 020 1002 123
    456789" → "… 456789" 노출). 그래서 전부 모으고, 겹치는 창은 detect()에서 합친다(옆 숫자까지
    가릴 수 있지만 더 가리는 쪽이라 안전하다). kinds[t]는 chain[t]와 chain[t+1] 사이 구분자의 종류다.
    """
    out: list[tuple[int, int]] = []
    for i in range(len(chain)):
        min_groups = 2 if (i + 1 < len(chain) and kinds[i] == "space") else 3
        total = chain[i][1] - chain[i][0]
        for j in range(i + 1, min(i + 4, len(chain))):
            if kinds[j - 1] != kinds[i] or chain[j - 1][1] - chain[j - 1][0] < 2:
                break  # 구분자가 바뀌었거나, 끝이 아닌 묶음이 한 자리다
            total += chain[j][1] - chain[j][0]
            if total > 14:
                break
            window = chain[i : j + 1]
            if (
                total >= 10
                and len(window) >= min_groups
                and not _looks_like_date_or_ip(text, window, kinds[i])
            ):
                out.append((chain[i][0], chain[j][1]))
    return out


def _separated_windows(text: str) -> list[tuple[int, int, int, int]]:
    """공백·점 등으로 나뉜 계좌번호 후보 창을 모두 찾는다(#474). 문맥 확인과 합치기는 detect()가 한다.

    돌려주는 값은 (창 시작, 창 끝, 사슬 시작, 사슬 끝)이다. 한 사슬은 한 줄에 이어 쓴 숫자라 문맥을
    함께 쓴다. 그래서 detect()는 창 앞뒤에 문맥이 없어도 사슬 앞뒤에 있으면 받는다
    ("입금 내역 3 2026 09 28 14 30 50000 1002 123 456789"의 계좌는 "입금"에서 15자 넘게 떨어져 있다).

    숫자 묶음을 앞에서부터 한 번 훑어 구분자로 이어진 사슬을 만들고, 사슬마다 창을 모은다. 사슬을
    끊는 곳은 셋이다.
    - 구분자가 아닌 틈(글자, 줄바꿈, 쉼표 등)
    - 7자리를 넘는 묶음. 계좌번호의 묶음이 아니다(10~14자리로 붙여 쓴 번호는 하이픈 식이 맡는다).
    - 붙여 쓴 하이픈으로 다른 숫자와 이어진 묶음. 하이픈 번호의 일부라 하이픈 식이 맡는다. 사슬에
      넣으면 "02 3456 7890 123-45-67891"의 전화번호와 사업자번호가 한 후보로 이어져, 파이프라인에서
      전화 종류가 보고되지 않았다. "계좌번호-1002 …"처럼 글자 뒤의 하이픈은 숫자를 잇지 않으므로 끊지 않는다.
    """
    groups = [(m.start(), m.end()) for m in _DIGIT_GROUP_RE.finditer(text)]
    windows: list[tuple[int, int, int, int]] = []
    chain: list[tuple[int, int]] = []
    kinds: list[str] = []

    def close_chain() -> None:
        """지금까지 이은 사슬의 창을 사슬 범위와 함께 모은다."""
        if chain:
            span = (chain[0][0], chain[-1][1])
            windows.extend((s, e, *span) for s, e in _chain_windows(text, chain, kinds))

    for idx, (start, end) in enumerate(groups):
        joined_before = idx > 0 and groups[idx - 1][1] == start - 1 and text[start - 1] == "-"
        joined_after = idx + 1 < len(groups) and groups[idx + 1][0] == end + 1 and text[end] == "-"
        if joined_before or joined_after or end - start > _MAX_GROUP_DIGITS:
            close_chain()
            chain, kinds = [], []
            continue
        if chain:
            kind = _separator_kind(text[chain[-1][1] : start])
            if kind is None:
                close_chain()
                chain, kinds = [], []
            else:
                kinds.append(kind)
        chain.append((start, end))
    close_chain()
    return windows


class AccountDetector(Detector):
    """계좌번호 탐지기 (문맥어 기반, 체크섬 없음)."""

    kind = "account"

    def detect(self, text: str) -> list[Detection]:
        """자릿수(10~14)와 문맥을 둘 다 확인한 후보를 확신도 0.6으로 돌려준다.

        공백·점 표기는 10~14자리 창을 합친 구간이라, 합친 뒤에는 14자리를 넘을 수 있다.

        계좌번호는 체크섬이 없어 형식만으로는 주문번호 같은 숫자열과 구분되지 않는다.
        그래서 후보 앞뒤 _CUE_WINDOW(15자) 안에 _ALL_CUES('은행'·'뱅크'나 '계좌'·'입금' 같은
        계좌 관련어)가 있거나, 은행 이름이 문맥으로 있어야 한다(_has_bank_name_cue).
        '우리'·'하나' 같은 일상어 은행 이름은 번호 바로 앞에 붙을 때만 문맥으로 본다.
        공백·점 등으로 나눈 번호는 그 번호가 들어 있는 숫자 줄(사슬) 앞뒤의 문맥도 함께 본다.
        """
        found: list[Detection] = []
        for m in _ACCOUNT_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if not (10 <= len(digits) <= 14):
                continue  # 한국 계좌번호 자릿수 범위 밖은 계좌가 아니다
            if not _has_account_context(text, m.start(), m.end()):
                continue  # 계좌 관련어도 은행 이름도 없으면 그냥 숫자열이므로 버린다
            found.append(self._detection(text, m.start(), m.end()))

        # 공백·점 등으로 나눈 표기(#474)는 따로 찾아 더한다. 위 하이픈 탐지는 건드리지 않는다.
        # 창이나 그 창이 속한 사슬 앞뒤에 문맥이 있는 창만 남기고, 겹치는 창은 하나로 합친다(더 가리기 = 안전).
        # 사슬 문맥은 사슬마다 한 번만 확인한다. 창마다 사슬 전체를 다시 보면 아주 긴 사슬에서 제곱 시간이 된다.
        chain_context: dict[tuple[int, int], bool] = {}
        kept: list[tuple[int, int]] = []
        for start, end, chain_start, chain_end in _separated_windows(text):
            if not _has_account_context(text, start, end):
                chain = (chain_start, chain_end)
                if chain not in chain_context:
                    chain_context[chain] = _has_account_context(text, chain_start, chain_end)
                if not chain_context[chain]:
                    continue
            kept.append((start, end))
        kept.sort()
        merged: list[tuple[int, int]] = []
        for start, end in kept:
            if merged and start < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        found.extend(self._detection(text, start, end) for start, end in merged)

        found.sort(key=lambda d: d.start)
        return found

    def _detection(self, text: str, start: int, end: int) -> Detection:
        """text[start:end]를 계좌번호 탐지 한 건으로 만든다. 체크섬이 없어 확신도는 0.6이다."""
        return Detection(
            kind=self.kind,
            start=start,
            end=end,
            text=text[start:end],
            confidence=0.6,
            detector=self.__class__.__name__,
        )
