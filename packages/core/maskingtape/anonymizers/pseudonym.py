"""가명처리 전략 — 탐지 구간을 그럴듯한 가짜 값으로 치환한다.

mask(****)·label([전화번호])와 달리 문장 구조가 살아 있어, LLM에 넘기기 전 전처리나
데이터셋 공유에 적합하다.
    예: "홍길동님께 010-1234-5678로 연락" → "김서준님께 010-8842-1097로 연락"

같은 원본값은 같은 가명으로 치환되어(호출 단위 일관성) "그 사람"이라는 문맥이 유지된다.

🔒 보안 설계:
1. 가명은 apply() 호출마다 새로 무작위 생성한다. 전역 결정적 매핑(같은 입력→항상 같은
   출력)을 두지 않는다 — 두면 매핑 테이블로 원본을 복원할 수 있다. (재현이 필요한
   테스트에서만 seed를 준다.)
2. 주민등록번호·카드번호는 형식만 유지하고 **체크섬을 일부러 통과하지 않게** 만든다.
   유효한 번호를 생성하면 실존 인물의 것과 겹치거나 유효한 개인정보로 악용될 수 있다.
   진짜 탐지기의 검증 함수를 재사용해 "검증하면 가짜"임을 보장한다.
3. 탐지된 구간은 종류를 불문하고 전부 치환한다. 생성기가 없는 종류도 라벨로 가려
   원본이 남지 않게 한다("덜 가리기"는 유출).

※ 생성된 값은 가짜지만 형식이 그럴듯해 실제 정보와 우연히 겹칠 수 있다. 반드시
  '가짜 데이터'로만 취급한다.
"""

from __future__ import annotations

import random
import string
from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.anonymizers.label import DEFAULT_LABELS
from maskingtape.detectors.financial.creditcard import _luhn_ok
from maskingtape.detectors.identity.rrn import _checksum_ok
from maskingtape.types import Detection

# 가짜 이름 재료 — 흔한 성/이름 음절 조합으로 그럴듯하게 만든다(전부 합성).
_SURNAMES = "김이박최정강조윤장임한오서신권황안송류전"
_GIVEN_NAMES = [
    "서준", "하은", "도윤", "지우", "예준", "지호", "수아", "지민", "서연", "하준",
    "민준", "지아", "예린", "시우", "주원", "유진", "채원", "은우", "다은", "현우",
]
# 가짜 주소 재료 — 실제 행정구역명 조합(특정 개인과 무관한 일반 지명).
_CITIES = ["서울특별시", "부산광역시", "대구광역시", "인천광역시", "대전광역시", "광주광역시"]
_GU = ["강남구", "마포구", "수영구", "유성구", "해운대구", "노원구", "서초구", "광진구"]
_DONG = ["역삼동", "합정동", "광안동", "봉명동", "우동", "상계동", "서초동", "자양동"]


class PseudonymAnonymizer(Anonymizer):
    """탐지 구간을 종류별 그럴듯한 가짜 값으로 치환한다(가명처리).

    seed: 재현이 필요한 테스트용. None(기본)이면 호출마다 다른 가명이 나온다.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        rng = random.Random(self._seed)

        # 같은 (종류, 원본값)에는 같은 가명을 배정한다(문맥 일관성). 배정은 등장 순서로,
        # 치환은 위치가 밀리지 않게 뒤→앞으로 한다.
        mapping: dict[tuple[str, str], str] = {}
        for d in sorted(detections, key=lambda d: d.start):
            key = (d.kind, d.text)
            if key not in mapping:
                mapping[key] = self._fake_value(d.kind, rng)

        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            fake = mapping[(d.kind, d.text)]
            text = text[: d.start] + fake + text[d.end :]
        return text

    def _fake_value(self, kind: str, rng: random.Random) -> str:
        generator = _GENERATORS.get(kind)
        if generator is None:
            # 생성기가 없는 종류도 반드시 가린다 — 원본을 남기면 유출이다.
            return f"[{DEFAULT_LABELS.get(kind, kind)}]"
        return generator(rng)


def _fake_name(rng: random.Random) -> str:
    return rng.choice(_SURNAMES) + rng.choice(_GIVEN_NAMES)


def _fake_phone(rng: random.Random) -> str:
    return f"010-{rng.randint(0, 9999):04d}-{rng.randint(0, 9999):04d}"


def _fake_email(rng: random.Random) -> str:
    # 회사 도메인과 겹치지 않도록 예시 전용 도메인(RFC 2606)만 쓴다.
    local = "".join(rng.choices(string.ascii_lowercase, k=rng.randint(5, 9)))
    return f"{local}@example.com"


def _fake_rrn(rng: random.Random) -> str:
    """형식만 그럴듯한 가짜 주민등록번호 — 체크섬을 통과하지 않도록 보장한다."""
    while True:
        yy, mm, dd = rng.randint(0, 99), rng.randint(1, 12), rng.randint(1, 28)
        gender = rng.randint(1, 4)  # 1~4: 내국인(1900/2000년대). dd는 28 이하라 항상 유효 날짜.
        digits = f"{yy:02d}{mm:02d}{dd:02d}{gender}{rng.randint(0, 999999):06d}"
        if not _checksum_ok(digits):  # 진짜 검증기로 확인 — 통과하면 진짜 같은 가짜라 다시 만든다
            return f"{digits[:6]}-{digits[6:]}"


def _fake_card(rng: random.Random) -> str:
    """형식만 그럴듯한 가짜 카드번호 — Luhn 체크섬을 통과하지 않도록 보장한다."""
    while True:
        digits = "".join(rng.choices(string.digits, k=16))
        if not _luhn_ok(digits):
            return f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:]}"


def _fake_address(rng: random.Random) -> str:
    city, gu, dong = rng.choice(_CITIES), rng.choice(_GU), rng.choice(_DONG)
    return f"{city} {gu} {dong} {rng.randint(1, 499)}-{rng.randint(1, 99)}"


_GENERATORS = {
    "name": _fake_name,
    "phone": _fake_phone,
    "email": _fake_email,
    "rrn": _fake_rrn,
    "card": _fake_card,
    "address": _fake_address,
}
