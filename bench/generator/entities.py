"""개인정보 종류별 합성 값 생성기.

모든 값은 난수로 조합해 생성한다 — 실존 인물·번호와 무관한 가짜 데이터만 만든다.
kind 문자열은 core의 Detection.kind와 동일하게 맞춘다: rrn, phone, email, name, address.

표기 형식(구분자·자릿수 등)도 core 탐지기가 실제로 허용하는 범위 안에서 무작위로 섞는다
(예: 전화번호 하이픈/공백/구분자 없음) — 실제 문서에서 나타나는 표기 다양성을 반영한다.

difficulty 파라미터로 표기 난이도를 제어한다:
- "easy": 구분자가 명확한 표준 표기 (하이픈, 지번 주소 등) — 탐지가 쉬운 형태
- "hard": 구분자 없음/국제표기/도로명+아파트처럼 길고 모호한 형태 — 탐지가 어려운 형태
- "mixed"(기본값): 위 둘을 무작위로 섞음
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

_PHONE_SEPARATORS_MIXED = ["-", "-", "-", " ", ".", ""]  # 하이픈이 가장 흔한 표기라 가중치를 둔다.
_PHONE_SEPARATORS_HARD = ["", ".", " "]  # 하이픈 없는(탐지가 상대적으로 더 까다로운) 표기만.
# phone.py의 _LANDLINE_RE가 허용하는 지역번호만 나열한다(그 외는 core가 아예 안 잡음).
_LANDLINE_AREA_CODES = [
    "02",
    "031", "032", "033",
    "041", "042", "043", "044",
    "051", "052", "053", "054", "055",
    "061", "062", "063", "064",
    "070",
]
_RRN_SEPARATORS_MIXED = ["-", "-", "-", " ", ""]  # RRN 정규식은 '.'을 구분자로 허용하지 않는다(rrn.py 참고).
_RRN_SEPARATORS_HARD = ["", " "]

# (접두사, 전체 자릿수) — 업계 표준 IIN/BIN 대역만 쓰고 나머지는 난수로 채운다(실제 발급 번호 아님).
# Visa=4로 시작 16자리, Mastercard=51~55로 시작 16자리, Amex=34/37로 시작 15자리.
_CARD_PREFIXES = [
    ("4", 16), ("4", 16), ("4", 16),  # Visa가 가장 흔하니 가중치를 둔다.
    ("51", 16), ("52", 16), ("53", 16), ("54", 16), ("55", 16),
    ("34", 15), ("37", 15),
]
_CARD_SEPARATORS_MIXED = ["-", "-", " ", ".", ""]
# creditcard.py의 정규식은 그룹 사이 구분자가 전부 동일해야 매칭된다(역참조 \1) — 하나만 골라 반복.

DIFFICULTIES = ("easy", "hard", "mixed")


@dataclass(frozen=True)
class Entity:
    """생성된 개인정보 값 하나."""

    kind: str
    text: str


def gen_name(rng: random.Random, difficulty: str = "mixed") -> Entity:
    surname = rng.choice(_SURNAMES)
    if difficulty == "easy":
        given_len = 2  # 2음절 이름이 더 명확하고 흔한 표준 형태
    elif difficulty == "hard":
        given_len = 1  # 1음절 이름은 더 짧고 흔한 단어와 헷갈리기 쉽다
    else:
        given_len = rng.choice([1, 2])
    given = "".join(rng.sample(_GIVEN_SYLLABLES, k=given_len))
    return Entity(kind="name", text=surname + given)


def gen_phone(rng: random.Random, difficulty: str = "mixed") -> Entity:
    if difficulty == "easy":
        sep = "-"
        variant = rng.choices(["mobile", "landline"], weights=[3, 1])[0]
    elif difficulty == "hard":
        sep = rng.choice(_PHONE_SEPARATORS_HARD)
        variant = rng.choices(["mobile", "landline", "intl"], weights=[4, 2, 3])[0]
    else:
        sep = rng.choice(_PHONE_SEPARATORS_MIXED)
        variant = rng.choices(["mobile", "landline", "intl"], weights=[6, 2, 1])[0]

    mid_len = 4
    if variant == "intl":
        # 국가번호 표기 (앞자리 0 생략) — PhoneDetector의 +82 분기 커버.
        prefix = f"+82{sep}1{rng.choice('016789')}"
    elif variant == "landline":
        # 유선전화 — 자택·사무실 번호. 서울(02)은 국번이 3자리인 경우도 흔해 길이를 섞는다.
        prefix = rng.choice(_LANDLINE_AREA_CODES)
        mid_len = rng.choice([3, 4])
    else:
        prefix = rng.choice(["010", "011", "016", "017", "018", "019"])
    mid = f"{rng.randint(0, 10**mid_len - 1):0{mid_len}d}"
    last = f"{rng.randint(0, 9999):04d}"
    return Entity(kind="phone", text=f"{prefix}{sep}{mid}{sep}{last}")


def gen_email(rng: random.Random, difficulty: str = "mixed") -> Entity:
    local = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz0123456789.", k=rng.randint(5, 10))).strip(".")
    if rng.random() < 0.2:
        # plus 표기(user+tag@) — email.py의 로컬 파트 문자 집합에 "+"가 포함돼 있어 실제로 잡힌다.
        tag = "".join(rng.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=rng.randint(2, 6)))
        local = f"{local}+{tag}"

    domain = rng.choice(_EMAIL_DOMAINS)
    if rng.random() < 0.2:
        # 서브도메인(mail.example.com) — email.py의 도메인 라벨이 여러 개(최대 8개) 이어져도 잡힌다.
        subdomain = rng.choice(["mail", "corp", "team", "biz"])
        domain = f"{subdomain}.{domain}"
    return Entity(kind="email", text=f"{local}@{domain}")


def gen_rrn(rng: random.Random, difficulty: str = "mixed") -> Entity:
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

    if difficulty == "easy":
        sep = "-"
    elif difficulty == "hard":
        sep = rng.choice(_RRN_SEPARATORS_HARD)
    else:
        sep = rng.choice(_RRN_SEPARATORS_MIXED)
    return Entity(kind="rrn", text=f"{front}{sep}{century_code}{serial}{check}")


def _luhn_check_digit(payload: str) -> str:
    """payload(체크 숫자를 뺀 나머지 자릿수)에 이어 붙이면 Luhn 검증을 통과하는 마지막 숫자를 계산한다.

    core의 creditcard.py `_luhn_ok`와 정확히 같은 규칙(오른쪽에서 두 번째 자리마다 2배,
    9 초과면 9를 뺌)을 거꾸로 풀어 체크 숫자를 구한다 — 검증 로직과 생성 로직이 어긋나면
    우리가 만든 "유효한 카드번호"가 실제로는 core에 안 잡히는 모순이 생긴다.
    """
    total = 0
    for index, char in enumerate(reversed(payload)):
        value = int(char)
        if index % 2 == 0:  # 체크 숫자가 뒤에 붙으면 이 자리가 오른쪽에서 두 번째가 된다
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return str((10 - total % 10) % 10)


def gen_card(rng: random.Random, difficulty: str = "mixed") -> Entity:
    prefix, total_len = rng.choice(_CARD_PREFIXES)
    body_len = total_len - len(prefix) - 1  # 체크 숫자 1자리를 뺀 나머지
    body = "".join(str(rng.randint(0, 9)) for _ in range(body_len))
    digits = prefix + body + _luhn_check_digit(prefix + body)

    if difficulty == "easy":
        sep = "-"
    elif difficulty == "hard":
        sep = ""  # 구분자 없이 붙여 쓴 형태 — creditcard.py의 "붙여쓰기 13~19자리" 분기
    else:
        sep = rng.choice(_CARD_SEPARATORS_MIXED)

    if not sep:
        text = digits
    elif len(digits) == 16:
        text = sep.join([digits[0:4], digits[4:8], digits[8:12], digits[12:16]])
    else:  # 15자리 Amex 계열은 4-6-5로 묶는다
        text = sep.join([digits[0:4], digits[4:10], digits[10:15]])
    return Entity(kind="card", text=text)


# 국세청 사업자등록번호 검증 가중치 — core의 business_registration.py `_checksum_ok`와 동일.
_BIZ_REG_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 5)


def _biz_reg_check_digit(front9: str) -> str:
    """앞 9자리(front9)에 이어 붙이면 국세청 검증을 통과하는 마지막(10번째) 자리를 계산한다.

    core의 business_registration.py `_checksum_ok`와 정확히 같은 규칙(가중합 + 9번째 자리×5의
    십의 자리 보정, 10에서 일의 자리를 뺌)을 거꾸로 풀어 체크 숫자를 구한다 — 계산이 어긋나면
    우리가 만든 "유효한 사업자등록번호"가 실제로는 core에 안 잡히는 모순이 생긴다.
    """
    total = sum(int(d) * w for d, w in zip(front9, _BIZ_REG_WEIGHTS))
    total += (int(front9[8]) * 5) // 10
    return str((10 - total % 10) % 10)


def gen_biz_reg(rng: random.Random, difficulty: str = "mixed") -> Entity:
    """사업자등록번호(XXX-XX-XXXXX). core는 하이픈 표기 + 유효 체크섬만 잡으므로(#123) 그
    형태만 만든다 — 표기 다양성(구분자 등)을 둘 여지가 core 쪽에 아예 없다.
    """
    g1 = f"{rng.randint(100, 999)}"
    g2 = f"{rng.randint(10, 99)}"
    g3_front = f"{rng.randint(0, 9999):04d}"
    check = _biz_reg_check_digit(g1 + g2 + g3_front)
    return Entity(kind="biz_reg", text=f"{g1}-{g2}-{g3_front}{check}")


def gen_address(rng: random.Random, difficulty: str = "mixed") -> Entity:
    if difficulty == "easy":
        use_road = False  # 지번 주소가 더 짧고 표준적인 형태
    elif difficulty == "hard":
        use_road = True  # 도로명 + 아파트 동/호는 더 길고 구조가 복잡함
    else:
        use_road = rng.random() < 0.5

    city = rng.choice(_CITIES)
    if not use_road:
        gu_dong = rng.choice(_GU_DONG)
        bunji = rng.randint(1, 999)
        ho = rng.randint(1, 20)
        base = f"{city} {gu_dong} {bunji}-{ho}"
    else:
        road = rng.choice(_ROAD_ADDRESSES)
        base = f"{city} {road}{rng.randint(1, 300)}길 {rng.randint(1, 90)}"
        if difficulty == "hard" or rng.random() < 0.5:
            apt = rng.choice(_APARTMENT_NAMES)
            base += f" {apt}아파트 {rng.randint(101, 130)}동 {rng.randint(101, 2005)}호"
    return Entity(kind="address", text=base)


_GENERATORS = {
    "name": gen_name,
    "phone": gen_phone,
    "email": gen_email,
    "rrn": gen_rrn,
    "address": gen_address,
    "card": gen_card,
    "biz_reg": gen_biz_reg,
}

ALL_KINDS = tuple(_GENERATORS.keys())


def generate_entity(kind: str, rng: random.Random, difficulty: str = "mixed") -> Entity:
    return _GENERATORS[kind](rng, difficulty)
