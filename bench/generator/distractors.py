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

# core RRNDetector가 허용하는 지역번호(rrn.py 참고)에 없는 국번 — 형식은 유선전화 같지만 매칭되면 안 됨.
_INVALID_AREA_CODES = ["09", "07", "00", "08"]


def gen_order_number(rng: random.Random) -> str:
    return f"ORD-{rng.randint(2024, 2026)}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}-{rng.randint(1000, 9999)}"


def gen_business_reg_number(rng: random.Random) -> str:
    """사업자등록번호 (ddd-dd-ddddd) — RRN(6+7)·전화(지역번호+7~8) 어느 자릿수 패턴과도 다르다."""
    return f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10000, 99999)}"


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


_DISTRACTOR_GENERATORS = [
    gen_order_number,
    gen_business_reg_number,
    gen_zip_code,
    gen_price,
    gen_date,
    gen_tracking_number,
    gen_invalid_phone_like,
    gen_invalid_rrn_like,
]


def generate_distractor(rng: random.Random) -> str:
    """개인정보가 아닌 값 하나를 무작위로 생성한다 (라벨 없이 문장에 심어진다)."""
    return rng.choice(_DISTRACTOR_GENERATORS)(rng)
