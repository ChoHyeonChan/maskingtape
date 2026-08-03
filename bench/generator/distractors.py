"""개인정보가 아닌 '헷갈리는' 문자열 생성기 — 오탐(false positive) 테스트용.

동작 원리:
1. 주문번호·사업자등록번호·날짜·가격처럼 숫자가 섞여 있지만 개인정보는 아닌 값을 만든다.
2. 전화번호·주민번호와 자릿수/구분자가 비슷하지만 실제 규칙(지역번호, 생년월일)은 어긋나는
   '아슬아슬한' 값도 포함한다 — core 탐지기가 형식만 보고 잘못 잡아내는지 확인하는 용도.
이 값들은 documents.py에서 라벨 없이 문장에 심어지므로, 평가 시 core가 이 구간을 개인정보로
잡아내면 그대로 FP(오탐)로 집계된다.
"""

from __future__ import annotations

import random

from bench.generator.entities import _biz_reg_check_digit, _PASSPORT_TYPE_CODES

# core RRNDetector가 허용하는 지역번호(rrn.py 참고)에 없는 국번 — 형식은 유선전화 같지만 매칭되면 안 됨.
_INVALID_AREA_CODES = ["09", "07", "00", "08"]

# 시/도 없이 시/군으로 시작하는 주소를 탐지하는 규칙(#118 관련 core #68/#117)이 지역 언급까지
# 오탐하면 안 되는 경계 케이스 — 조사 '로'가 공백 없이 붙거나(성남시로), 구만 단독으로 오는 경우.
_REGION_MENTION_PHRASES = [
    "성남시로", "김포시로", "수원시로", "용인시로",
    "강남구에서", "분당구에서", "영통구에서",
]


def gen_order_number(rng: random.Random) -> str:
    return f"ORD-{rng.randint(2024, 2026)}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}-{rng.randint(1000, 9999)}"


def gen_business_reg_number(rng: random.Random) -> str:
    """사업자등록번호 모양(ddd-dd-ddddd)이지만 체크섬은 항상 무효인 문자열 —
    BusinessRegistrationDetector가 걸러내야 정상.

    core는 국세청 검증 체크섬이 맞는 번호만 사업자등록번호로 잡는다(business_registration.py).
    체크 자리까지 완전 난수로 뽑으면 10자리 중 하나(약 10% 확률)로 우연히 체크섬이 맞아
    오탐이 생길 수 있어(#123), 유효 체크 숫자를 계산한 뒤 일부러 다른 숫자로 바꿔 항상
    무효가 되게 만든다.
    """
    front9 = f"{rng.randint(100, 999)}{rng.randint(10, 99)}{rng.randint(0, 9999):04d}"
    valid_check = int(_biz_reg_check_digit(front9))
    invalid_check = (valid_check + rng.randint(1, 9)) % 10
    return f"{front9[:3]}-{front9[3:5]}-{front9[5:]}{invalid_check}"


def gen_zip_code(rng: random.Random) -> str:
    return f"{rng.randint(10000, 63999)}"


def gen_price(rng: random.Random) -> str:
    return f"{rng.randint(1000, 999000):,}원"


def gen_date(rng: random.Random) -> str:
    return f"{rng.randint(2020, 2026)}.{rng.randint(1, 12):02d}.{rng.randint(1, 28):02d}"


def gen_tracking_number(rng: random.Random) -> str:
    letters = "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    return f"{letters}{rng.randint(100000000, 999999999)}KR"


def gen_invalid_phone_like(rng: random.Random) -> str:
    """지역번호가 존재하지 않는 '전화번호 모양' 문자열 — PhoneDetector가 걸러내야 정상."""
    area = rng.choice(_INVALID_AREA_CODES)
    return f"0{area[1]}-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"


def gen_invalid_rrn_like(rng: random.Random) -> str:
    """존재하지 않는 날짜(13월 등)로 만든 '주민번호 모양' 문자열 — RRNDetector가 걸러내야 정상."""
    month = rng.randint(13, 19)  # 실제 없는 월
    day = rng.randint(32, 39)  # 실제 없는 일
    front = f"{rng.randint(0, 99):02d}{month}{day}"
    back = f"{rng.randint(1, 4)}{rng.randint(0, 999999):06d}"
    return f"{front}-{back}"


def gen_region_mention_like(rng: random.Random) -> str:
    """시/군 이름에 조사 '로'가 붙거나 구만 단독으로 오는 지역 언급 — AddressDetector가 걸러내야 정상."""
    return rng.choice(_REGION_MENTION_PHRASES)


def gen_passport_like_code(rng: random.Random) -> str:
    """여권번호 모양(M/S/R/O/D + 숫자)이지만 자릿수가 하나 어긋난 코드 — PassportDetector가
    걸러내야 정상.

    core는 체크섬이 없어(passport.py) 정확한 자릿수(8자리, 또는 3자리+문자+4자리)만으로
    판별한다 — 그래서 gen_business_reg_number처럼 "체크섬 무효화"는 못 쓰고, 대신 자릿수를
    하나 빼거나 더해 사원번호·상품 시리얼처럼 실제 업무에 흔한 근접 미스를 만든다.
    """
    code = rng.choice(_PASSPORT_TYPE_CODES)
    digit_count = rng.choice([7, 9])  # 구여권 형식(8자리)과 자릿수만 다르게
    digits = f"{rng.randint(0, 10**digit_count - 1):0{digit_count}d}"
    return f"{code}{digits}"


_DISTRACTOR_GENERATORS = [
    gen_order_number,
    gen_business_reg_number,
    gen_zip_code,
    gen_price,
    gen_date,
    gen_tracking_number,
    gen_invalid_phone_like,
    gen_invalid_rrn_like,
    gen_region_mention_like,
    gen_passport_like_code,
]


def generate_distractor(rng: random.Random) -> str:
    """개인정보가 아닌 값 하나를 무작위로 생성한다 (라벨 없이 문장에 심어진다)."""
    return rng.choice(_DISTRACTOR_GENERATORS)(rng)
