"""계좌번호 탐지기 — 문맥어(은행명·계좌 관련어) 필수 + 숫자 그룹 패턴.

동작 원리:
1. 한국 계좌번호는 **체크섬이 없고 은행별 형식이 제각각**(2~4개 하이픈 그룹, 총 10~14자리)이라,
   형식만으로 잡으면 주문번호·일련번호 같은 무관한 숫자열을 오탐한다.
2. 그래서 은행명("국민","신한"…)이나 계좌 관련어("계좌","입금","이체"…)가 매치 근처(±15자)에
   있을 때만 탐지한다 — 문맥이 없으면 버린다. (사업자등록번호 교훈: 체크섬이 없으면 문맥 + 측정.)
3. 체크섬이 없어 확신도는 0.6으로 낮춘다.

보안: 계좌번호 누락은 금융정보 유출이다. 그래서 문맥이 있을 때는 놓치지 않도록 하이픈 그룹과
붙여 쓴 숫자를 모두 잡되, 반복에 상한을 둬 ReDoS를 막는다(모든 수량자가 유한 범위).
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

# 하이픈으로 나뉜 2~7자리 그룹(2~4개) 또는 붙여 쓴 10~14자리. 7자리 그룹은 카카오뱅크식
# "3333-01-1234567"의 마지막 묶음까지 담기 위함이다. 앞뒤가 숫자/하이픈이면 더 긴 번호의
# 일부이므로 경계로 제외한다. 총 자릿수(10~14) 검증은 detect에서 한다.
_ACCOUNT_RE = re.compile(r"(?<![\d-])(?:\d{2,7}(?:-\d{2,7}){1,3}|\d{10,14})(?![\d-])")

# 문맥어 — 하나라도 매치 근처에 있어야 계좌로 본다.
# 은행 고유명("국민","하나","우리","제일"…)은 흔한 일반 단어에 그대로 들어가("결제일"의 "제일",
# "우리 회사"의 "우리") 오탐을 만든다. 그래서 개별 은행명 대신 "은행"·"뱅크"(어느 은행이든
# 이 접미어가 붙는다) + 계좌 행위어만 쓴다. 이 단어들은 무관한 단어의 부분열로 잘 끼지 않는다.
_ALL_CUES = (
    "계좌", "입금", "이체", "예금주", "예금", "출금", "송금", "은행", "뱅크",
)

# 문맥어를 찾는 창(문자 수) — 매치 앞뒤로 이만큼 본다. "국민은행 123-…"(앞)과 "123-… 로 입금"(뒤) 모두 커버.
_CUE_WINDOW = 15


class AccountDetector(Detector):
    """계좌번호 탐지기 (문맥어 기반, 체크섬 없음)."""

    kind = "account"

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for m in _ACCOUNT_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group(0))
            if not (10 <= len(digits) <= 14):
                continue  # 한국 계좌번호 자릿수 범위 밖은 계좌가 아니다

            left = max(0, m.start() - _CUE_WINDOW)
            context = text[left : m.end() + _CUE_WINDOW]
            if not any(cue in context for cue in _ALL_CUES):
                continue  # 은행명·계좌 관련어가 근처에 없으면 그냥 숫자열이므로 버린다

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
