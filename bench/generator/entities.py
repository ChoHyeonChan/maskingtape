"""개인정보 종류별 합성 값 생성기.

모든 값은 난수로 조합해 생성한다 — 실존 인물·번호와 무관한 가짜 데이터만 만든다.
kind 문자열은 core의 Detection.kind와 동일하게 맞춘다: rrn, phone, email, name, address.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

_SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
_GIVEN_SYLLABLES = ["민", "서", "지", "하", "은", "도", "현", "우", "준", "아", "윤", "율", "찬", "빈"]

_GU_DONG = ["강남구 역삼동", "마포구 합정동", "종로구 청운동", "수영구 광안동", "유성구 봉명동"]
_CITIES = ["서울특별시", "부산광역시", "대전광역시", "인천광역시", "대구광역시"]

_EMAIL_DOMAINS = ["example.com", "mail-test.kr", "sample.org", "testmail.net"]

# rrn.py의 체크섬 검증 로직과 동일한 가중치 — 생성기가 만드는 번호도 유효하게 만든다.
_RRN_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)


@dataclass(frozen=True)
class Entity:
    """생성된 개인정보 값 하나."""

    kind: str
    text: str


def gen_name(rng: random.Random) -> Entity:
    surname = rng.choice(_SURNAMES)
    given = "".join(rng.sample(_GIVEN_SYLLABLES, k=rng.choice([1, 2])))
    return Entity(kind="name", text=surname + given)


def gen_phone(rng: random.Random) -> Entity:
    prefix = rng.choice(["010", "011", "016", "017", "018", "019"])
    mid = f"{rng.randint(0, 9999):04d}"
    last = f"{rng.randint(0, 9999):04d}"
    return Entity(kind="phone", text=f"{prefix}-{mid}-{last}")


def gen_email(rng: random.Random) -> Entity:
    local = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz0123456789.", k=rng.randint(5, 10))).strip(".")
    domain = rng.choice(_EMAIL_DOMAINS)
    return Entity(kind="email", text=f"{local}@{domain}")


def gen_rrn(rng: random.Random) -> Entity:
    year = rng.randint(1960, 2015)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    century_code = "3" if year >= 2000 else "1"  # 2000년대 출생 남성=3, 1900년대 남성=1 (rrn.py _CENTURY 기준)
    front = f"{year % 100:02d}{month:02d}{day:02d}"
    serial = f"{rng.randint(0, 99999):05d}"  # 뒷자리 7개 = 성별코드(1) + 일련번호(5) + 검증번호(1)
    digits = front + century_code + serial  # 12자리 — 검증번호 계산 대상
    total = sum(int(d) * w for d, w in zip(digits, _RRN_WEIGHTS))
    check = (11 - total % 11) % 10
    return Entity(kind="rrn", text=f"{front}-{century_code}{serial}{check}")


def gen_address(rng: random.Random) -> Entity:
    city = rng.choice(_CITIES)
    gu_dong = rng.choice(_GU_DONG)
    bunji = rng.randint(1, 999)
    ho = rng.randint(1, 20)
    return Entity(kind="address", text=f"{city} {gu_dong} {bunji}-{ho}")


_GENERATORS = {
    "name": gen_name,
    "phone": gen_phone,
    "email": gen_email,
    "rrn": gen_rrn,
    "address": gen_address,
}

ALL_KINDS = tuple(_GENERATORS.keys())


def generate_entity(kind: str, rng: random.Random) -> Entity:
    return _GENERATORS[kind](rng)
