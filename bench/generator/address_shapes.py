# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""core #423이 고친 주소 형태를 만드는 재료 — 벤치가 그 경계를 재게 한다(#431).

동작 원리:
1. 기존 생성기(entities.gen_address)는 도로명이 5개뿐이고 이름에 숫자·동·리가 든 도로명이나
   행정동이 없으며 읍·면 뒤 주소도 만들지 않아서, core가 #423(PR #427)에서 고친 형태가 벤치에
   한 건도 안 나왔다 — 주소 F1 1.000 뒤에 숨어 있던 사각지대다.
2. 이 모듈은 core `test_address.py`의 `# --- #423` 섹션이 "한 구간으로 잡혀야 한다"고 고정한
   8가지 형태를 형태별 함수로 만든다. 번지·건물번호는 난수(가짜)이고 지명은 공개 행정구역명이다.
3. 이 형태를 기본 생성에 섞으면 난수 흐름이 바뀌어 제출 수치의 근거인 synth_v1.jsonl을 다시 만들
   수 없게 된다. 그래서 gen_address는 `extended=True`일 때만 이 모듈을 부르고, 기본(v1)은
   난수를 하나도 더 쓰지 않는다.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable

# entities._APARTMENT_NAMES와 같은 용도지만, entities가 이 모듈을 import하므로(순환 방지) 따로 둔다.
_BUILDINGS = ["래미안", "자이", "푸르지오", "힐스테이트", "더샵"]

# 군 지역 — (시/도, 군, 읍·면, 그 읍·면의 도로명, 그 읍·면의 리). core 테스트가 쓰는 이름을 그대로 쓴다.
# 시/도 없이 군으로 시작하는 표기도 함께 만든다(아래 _NO_PROVINCE_RATE).
_COUNTY_AREAS = [
    ("경기도", "양평군", "양평읍", "양평시장길", "양근리"),
    ("전라남도", "해남군", "해남읍", "중앙1로", "해리"),
    ("경상북도", "칠곡군", "왜관읍", "중앙로", "왜관리"),
    ("강원특별자치도", "홍천군", "화촌면", "화촌로", "구성포리"),
]

# 이름 앞부분이 동·리로 끝나는 도로명 — "대동로"를 "대동"(동)까지만 잡고 끊던 문제(#423)가 있었다.
_DONG_RI_ROADS = [
    ("서울특별시", "강남구", "대동로"),
    ("서울특별시", "강서구", "화곡동로"),
    ("경기도", "성남시 분당구", "정자동로"),
    ("경기도", "김포시", "사우리로"),
]

# 이름에 숫자가 든 도로명. 세종시는 구가 없다(빈 문자열).
_DIGIT_ROADS = [
    ("부산광역시", "해운대구", "센텀2로"),
    ("세종특별자치시", "", "도움6로"),
]

# 이름에 숫자가 든 행정동.
_DIGIT_DONGS = [
    ("서울특별시", "관악구", "신림2동"),
    ("서울특별시", "노원구", "상계10동"),
    ("경기도", "성남시 분당구", "정자1동"),
]

# N가 동 — "을지로3가"의 "3가"가 동 자리다.
_N_GA_DONGS = [
    ("서울특별시", "중구", "을지로3가"),
    ("서울특별시", "종로구", "종로5가"),
]

# 동 뒤에 도로명을 덧붙여 쓰는 표기 — (시/도, 구, 동, 도로명).
_DONG_THEN_ROADS = [
    ("서울특별시", "강남구", "역삼동", "테헤란로"),
    ("서울특별시", "마포구", "합정동", "월드컵로"),
    ("서울특별시", "송파구", "잠실동", "올림픽로"),
]

# "올림픽로35가길"처럼 가길이 붙는 도로명 — (시/도, 구, 도로명 앞부분).
_GA_GIL_ROADS = [
    ("서울특별시", "송파구", "올림픽로"),
    ("서울특별시", "강남구", "테헤란로"),
]


# 군 지역 주소에서 시/도를 빼고 "양평군 양평읍 ..."으로 시작하는 비율 — 군 앵커로 잡히는 표기(#118)다.
# 500건 데이터셋의 군 지역 주소는 9건 안팎이라 0.3이면 한 건도 안 들어갈 수 있다(seed 42에서 실측 0건).
_NO_PROVINCE_RATE = 0.5


def _join(*parts: str) -> str:
    """빈 조각(세종시의 구)은 건너뛰고 공백으로 잇는다."""
    return " ".join(p for p in parts if p)


def _building_tail(rng: random.Random) -> str:
    """도로명 주소 뒤 건물 동·호 꼬리(30%) — core `_TAIL`이 건물명·동·호까지 한 구간으로 잇는다."""
    if rng.random() >= 0.3:
        return ""
    return f" {rng.choice(_BUILDINGS)}아파트 {rng.randint(101, 130)}동 {rng.randint(101, 2005)}호"


def _bunji(rng: random.Random) -> str:
    """지번 — 본번만이거나 본번-부번."""
    main = rng.randint(1, 999)
    return f"{main}-{rng.randint(1, 20)}" if rng.random() < 0.5 else str(main)


def _county_road(rng: random.Random) -> str:
    """읍·면 뒤 도로명 — 군 지역 도로명주소의 표준 형식. 예전엔 읍·면에서 멈춰 도로명이 샜다."""
    do, gun, eup, road, _ri = rng.choice(_COUNTY_AREAS)
    do = "" if rng.random() < _NO_PROVINCE_RATE else do
    return f"{_join(do, gun, eup, road)} {rng.randint(1, 400)}{_building_tail(rng)}"


def _county_ri(rng: random.Random) -> str:
    """읍·면 뒤 리(지번) — 군 지역 지번주소의 표준 형식. 예전엔 읍·면에서 멈춰 리·번지가 샜다."""
    do, gun, eup, _road, ri = rng.choice(_COUNTY_AREAS)
    do = "" if rng.random() < _NO_PROVINCE_RATE else do
    return f"{_join(do, gun, eup, ri)} {_bunji(rng)}"


def _dong_ri_road(rng: random.Random) -> str:
    do, area, road = rng.choice(_DONG_RI_ROADS)
    return f"{_join(do, area, road)} {rng.randint(1, 99)}{_building_tail(rng)}"


def _digit_road(rng: random.Random) -> str:
    do, area, road = rng.choice(_DIGIT_ROADS)
    return f"{_join(do, area, road)} {rng.randint(1, 99)}{_building_tail(rng)}"


def _digit_dong(rng: random.Random) -> str:
    do, area, dong = rng.choice(_DIGIT_DONGS)
    return f"{_join(do, area, dong)} {_bunji(rng)}"


def _n_ga_dong(rng: random.Random) -> str:
    do, area, dong = rng.choice(_N_GA_DONGS)
    return f"{_join(do, area, dong)} {rng.randint(1, 99)}"


def _dong_then_road(rng: random.Random) -> str:
    do, gu, dong, road = rng.choice(_DONG_THEN_ROADS)
    return f"{_join(do, gu, dong, road)} {rng.randint(1, 300)}{_building_tail(rng)}"


def _ga_gil(rng: random.Random) -> str:
    do, gu, road = rng.choice(_GA_GIL_ROADS)
    return f"{_join(do, gu)} {road}{rng.randint(1, 99)}가길 {rng.randint(1, 60)}"


# 형태 이름 → 생성 함수. 이름은 테스트가 형태별로 검증할 때 쓴다.
EXTENDED_SHAPES: dict[str, Callable[[random.Random], str]] = {
    "county_road": _county_road,
    "county_ri": _county_ri,
    "dong_ri_road": _dong_ri_road,
    "digit_road": _digit_road,
    "digit_dong": _digit_dong,
    "n_ga_dong": _n_ga_dong,
    "dong_then_road": _dong_then_road,
    "ga_gil": _ga_gil,
}


# 형태 이름 → 그 형태의 출력만 알아보는 정규식. 데이터셋에 8형태가 실제로 들어갔는지, 기본(v1) 생성이
# 새 형태를 섞지 않는지 검증할 때 쓴다(기존 gen_address의 지번·도로명 출력과는 겹치지 않는다).
SHAPE_MARKERS: dict[str, re.Pattern[str]] = {
    "county_road": re.compile(r"[읍면] \S+(?:로|길) \d+"),
    "county_ri": re.compile(r"[읍면] \S+리 \d+"),
    "dong_ri_road": re.compile(r"(?:대동로|화곡동로|정자동로|사우리로) \d+"),
    "digit_road": re.compile(r"(?:센텀2로|도움6로) \d+"),
    "digit_dong": re.compile(r"(?:신림2동|상계10동|정자1동) \d+"),
    "n_ga_dong": re.compile(r"(?:을지로3가|종로5가) \d+"),
    "dong_then_road": re.compile(r"동 (?:테헤란로|월드컵로|올림픽로) \d+"),
    "ga_gil": re.compile(r"로\d+가길 \d+"),
}


def gen_extended_address(rng: random.Random) -> str:
    """#423이 고친 8가지 형태 중 하나를 같은 확률로 골라 주소 한 건을 만든다."""
    name = rng.choice(list(EXTENDED_SHAPES))
    return EXTENDED_SHAPES[name](rng)
