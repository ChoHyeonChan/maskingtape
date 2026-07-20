"""개인정보 종류별 합성 값 생성기.

모든 값은 난수로 조합해 생성한다 — 실존 인물·번호와 무관한 가짜 데이터만 만든다.
kind 문자열은 core의 Detection.kind와 동일하게 맞춘다: rrn, phone, email, name, address.

표기 형식(구분자·자릿수 등)도 core 탐지기가 실제로 허용하는 범위 안에서 무작위로 섞는다
(예: 전화번호 하이픈/공백/구분자 없음) — 실제 문서에서 나타나는 표기 다양성을 반영한다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# 성씨 상위 30종(통계청 인구총조사 기준 다빈도 성씨) — 특정 인물이 아닌 통계적 분포만 참고.
_SURNAMES = [
    "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
    "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍",
    "유", "고", "문", "양", "손", "배", "백", "허", "남", "심",
]
_GIVEN_SYLLABLES = [
    "민", "서", "지", "하", "은", "도", "현", "우", "준", "아",
    "윤", "율", "찬", "빈", "재", "연", "수", "진", "영", "호",
    "규", "성", "훈", "경", "원", "석", "인", "혜", "정", "예",
]

_ROAD_ADDRESSES = ["테헤란로", "월드컵로", "판교역로", "센텀중앙로", "동성로"]
_GU_DONG = [
    "강남구 역삼동", "마포구 합정동", "종로구 청운동", "수영구 광안동", "유성구 봉명동",
    "해운대구 우동", "성남시 분당구 정자동", "수원시 영통구 매탄동", "광진구 자양동", "노원구 상계동",
]
_CITIES = ["서울특별시", "부산광역시", "대전광역시", "인천광역시", "대구광역시", "광주광역시", "울산광역시"]
_APARTMENT_NAMES = ["래미안", "자이", "푸르지오", "e편한세상", "힐스테이트", "더샵"]

# 실제 회사 도메인과 겹치지 않도록 합성/예시 전용 도메인만 사용한다.
_EMAIL_DOMAINS = [
    "example.com", "mail-test.kr", "sample.org", "testmail.net",
    "demo-corp.com", "sample-mail.net", "testcorp.io", "mail-sample.kr",
]

# rrn.py의 체크섬 검증 로직과 동일한 가중치 — 생성기가 만드는 번호도 유효하게 만든다.
_RRN_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)
# 성별코드 1/2=1900년대, 3/4=2000년대 (rrn.py _CENTURY 기준). 5~8(외국인)은 별도 표기라 제외.
_CENTURY_CODES = {1900: ("1", "2"), 2000: ("3", "4")}

_PHONE_SEPARATORS = ["-", "-", "-", " ", ".", ""]  # 하이픈이 가장 흔한 표기라 가중치를 둔다.
_RRN_SEPARATORS = ["-", "-", "-", " ", ""]  # RRN 정규식은 '.'을 구분자로 허용하지 않는다(rrn.py 참고).


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
    sep = rng.choice(_PHONE_SEPARATORS)
    if rng.random() < 0.15:
        # 국가번호 표기 (앞자리 0 생략) — PhoneDetector의 +82 분기 커버.
        prefix = f"+82{sep}1{rng.choice('016789')}"
    else:
        prefix = rng.choice(["010", "011", "016", "017", "018", "019"])
    mid = f"{rng.randint(0, 9999):04d}"
    last = f"{rng.randint(0, 9999):04d}"
    return Entity(kind="phone", text=f"{prefix}{sep}{mid}{sep}{last}")


def gen_email(rng: random.Random) -> Entity:
    local = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz0123456789.", k=rng.randint(5, 10))).strip(".")
    domain = rng.choice(_EMAIL_DOMAINS)
    return Entity(kind="email", text=f"{local}@{domain}")


def gen_rrn(rng: random.Random) -> Entity:
    century = rng.choice([1900, 2000])
    year = rng.randint(0, 99)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    century_code = rng.choice(_CENTURY_CODES[century])
    front = f"{year:02d}{month:02d}{day:02d}"
    serial = f"{rng.randint(0, 99999):05d}"  # 뒷자리 7개 = 성별코드(1) + 일련번호(5) + 검증번호(1)
    digits = front + century_code + serial  # 12자리 — 검증번호 계산 대상
    total = sum(int(d) * w for d, w in zip(digits, _RRN_WEIGHTS))
    check = (11 - total % 11) % 10
    sep = rng.choice(_RRN_SEPARATORS)
    return Entity(kind="rrn", text=f"{front}{sep}{century_code}{serial}{check}")


def gen_address(rng: random.Random) -> Entity:
    city = rng.choice(_CITIES)
    if rng.random() < 0.5:
        # 지번 주소
        gu_dong = rng.choice(_GU_DONG)
        bunji = rng.randint(1, 999)
        ho = rng.randint(1, 20)
        base = f"{city} {gu_dong} {bunji}-{ho}"
    else:
        # 도로명 주소 (+ 아파트 동/호 표기 확률적으로 추가)
        road = rng.choice(_ROAD_ADDRESSES)
        base = f"{city} {road}{rng.randint(1, 300)}길 {rng.randint(1, 90)}"
        if rng.random() < 0.5:
            apt = rng.choice(_APARTMENT_NAMES)
            base += f" {apt}아파트 {rng.randint(101, 130)}동 {rng.randint(101, 2005)}호"
    return Entity(kind="address", text=base)


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
