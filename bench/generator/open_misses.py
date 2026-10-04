# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""열린 미탐 세트(#610) — core 이슈로 올라가 있지만 아직 안 고쳐진 미탐 모양을 정답 라벨로 만든다.

표기 변형 세트(variants.py, #531)가 "이미 고친 표기"를 재서 되돌아가지 않는지 본다면, 이
세트는 "아직 안 고친 표기"를 재서 core가 고칠 때마다 이슈별 재현율이 오르는 걸 보인다.
synth_v1·v2는 이름을 뺀 종류가 전부 1.000이라 이런 개선이 점수에 안 보인다.

문장은 core 이슈 본문의 재현 문장과 **같은 모양**을 새로 쓴 합성 문장이다. 값(이름·번호·
주소)은 시드로 매번 새로 뽑고 틀만 이슈가 다룬 모양을 따른다.

라벨의 `target`은 "이 이슈가 놓친다고 보고한 자리"인지다. 같은 문서에 지금도 잡히는 개인정보가
함께 있을 때(나열의 첫 이름, 다시 나오는 이름의 첫 언급) 그 라벨은 `target: False`로 둔다.
재현율은 target 라벨로만 세고, 나머지는 오탐으로 세지 않기 위한 정답으로만 쓴다.

우리가 찾은 미탐만 모은 세트라 시작 재현율이 0에 가깝게 나오는 게 정상이다 — 일반
정확도가 아니라 "열린 미탐을 얼마나 막았는지" 보는 진행 지표로만 쓴다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from bench.generator.entities import (
    _BIZ_REG_WEIGHTS,
    _CITIES,
    _GIVEN_SYLLABLES,
    _GU_DONG,
    _GU_NAMES,
    _ROAD_ADDRESSES,
    _SURNAMES,
    _biz_reg_check_digit,
    _luhn_check_digit,
)

# 문장 조각. 문자열은 그대로 붙이고, (종류, 값)은 붙이면서 정답 라벨로 남긴다.
# (종류, 값, False)는 정답이지만 이 이슈의 대상(target)은 아닌 라벨이다.
Part = str | tuple[str, str] | tuple[str, str, bool]


@dataclass(frozen=True)
class MissDoc:
    text: str
    labels: list[dict]
    miss_tag: str
    issue: int


def _build(parts: list[Part], tag: str, issue: int) -> MissDoc:
    """조각을 이어 붙이면서 라벨 위치를 센다 — 위치를 손으로 계산하지 않아 어긋날 일이 없다."""
    text = ""
    labels: list[dict] = []
    for part in parts:
        if isinstance(part, str):
            text += part
            continue
        kind, value = part[0], part[1]
        label = {"kind": kind, "start": len(text), "end": len(text) + len(value)}
        if len(part) == 3 and not part[2]:
            label["target"] = False
        labels.append(label)
        text += value
    return MissDoc(text=text, labels=labels, miss_tag=tag, issue=issue)


def _has_batchim(char: str) -> bool:
    """한글 음절에 받침이 있는지. 음절 코드는 (초성·중성·종성) 순으로 놓여 28로 나눈 나머지가 종성이다."""
    return (ord(char) - 0xAC00) % 28 != 0


def _josa(word: str, with_batchim: str, without: str) -> str:
    """받침에 맞는 조사를 고른다(이/가, 은/는). synth_v1 템플릿처럼 한쪽으로 고정하면 비문이 나온다."""
    return with_batchim if _has_batchim(word[-1]) else without


def _josa_ro(word: str) -> str:
    """으로/로. 받침이 없거나 ㄹ 받침이면 '로'다(종성 번호 8이 ㄹ)."""
    jong = (ord(word[-1]) - 0xAC00) % 28
    return "로" if jong in (0, 8) else "으로"


def _name3(rng: random.Random) -> str:
    """성 + 두 글자 이름. 두 글자 이름(성+한 글자)의 한계와 섞이지 않게 대부분의 태그가 이걸 쓴다."""
    return rng.choice(_SURNAMES) + "".join(rng.sample(_GIVEN_SYLLABLES, k=2))


# 생성기의 성씨×이름 음절 조합 가운데 core가 일반 낱말로 거르는 두 글자(실측 7개). 이걸 섞으면
# "두 글자 이름 + 직함"(#601)과 "일반 낱말과 겹치는 이름"이 한 태그에서 뒤섞인다.
_TWO_SYLLABLE_COMMON_WORDS = frozenset({"문서", "배정", "신규", "양성", "유지", "이하", "조정"})


def _name2(rng: random.Random) -> str:
    while True:
        name = rng.choice(_SURNAMES) + rng.choice(_GIVEN_SYLLABLES)
        if name not in _TWO_SYLLABLE_COMMON_WORDS:
            return name


def _base_address(rng: random.Random) -> str:
    """시/도 정식명으로 시작해 번지까지 있는 주소 — 지금 core가 번지까지는 확실히 가리는 모양."""
    return f"{rng.choice(_CITIES)} {rng.choice(_GU_NAMES)} {rng.choice(_ROAD_ADDRESSES)} {rng.randint(1, 300)}"


# ── #589 "A에서 B로 변경" ─────────────────────────────────────────


def gen_name_change_log_second(rng: random.Random) -> MissDoc:
    """둘째 이름에는 단서가 없다. 첫 이름은 '담당자가'가 단서라 지금도 잡힌다(target 아님)."""
    role = rng.choice(["담당자", "보호자", "신청자"])
    first, second = _name3(rng), _name3(rng)
    return _build(
        [f"{role}가 ", ("name", first, False), "에서 ", ("name", second), f"{_josa_ro(second)} 변경되었습니다."],
        "name_change_log_second",
        589,
    )


# ── #592 날짜 뒤에 오는 생년월일 단서 ──────────────────────────────


def gen_birth_date_cue_after(rng: random.Random) -> MissDoc:
    """단서("생", "에 태어났", "이 생일")가 날짜 **뒤**에 온다. 앞에 라벨이 있으면 지금도 잡힌다."""
    year, month, day = rng.randint(1950, 2015), rng.randint(1, 12), rng.randint(1, 28)
    date = rng.choice([f"{year}년 {month}월 {day}일", f"{year % 100:02d}년 {month}월 {day}일"])
    lead, tail = rng.choice([
        ("저는 ", "생입니다."), ("", "생이에요."), ("막내는 ", "에 태어났어요."), ("", "이 제 생일이에요."),
    ])
    return _build([lead, ("birth_date", date), tail], "birth_date_cue_after", 592)


# ── #593 건물명 + 동·호만 쓴 주소 ──────────────────────────────────


def gen_address_building_dong_ho_only(rng: random.Random) -> MissDoc:
    """시·도나 도로명 없이 건물명부터 시작한다. 건물 종류는 core가 꼬리에서 이미 아는 낱말만 쓴다 —
    시작점이 없다는 것만 다르게 해서 #605(꼬리 유출)와 섞이지 않게 한다."""
    building = rng.choice(_BUILDING_STEMS) + rng.choice(["아파트", "빌라", "맨션", "오피스텔"])
    value = f"{building} {rng.randint(1, 120)}동 {rng.randint(1, 20)}{rng.randint(1, 9):02d}호"
    tail = rng.choice(["로 보내 주세요.", " 사시는 분이죠?", "입니다."])
    return _build([("address", value), tail], "address_building_dong_ho_only", 593)


# ── #594 지역 이름으로 시작하는 옛 운전면허번호 ────────────────────


def gen_driver_license_region_name(rng: random.Random) -> MissDoc:
    region = rng.choice(["서울", "경기", "부산", "전남", "대구", "강원"])
    value = f"{region} {rng.randint(0, 99):02d}-{rng.randint(0, 999999):06d}-{rng.randint(0, 99):02d}"
    label = rng.choice(["면허번호 ", "운전면허번호: ", "면허번호: "])
    return _build([label, ("driver_license", value), rng.choice(["입니다.", ""])], "driver_license_region_name", 594)


# ── #600 앞 단서 + 이름 + 목록에 없는 어미 ─────────────────────────

# 이름 끝 글자의 받침과 무관하게 붙는 어미.
_ENDINGS_ANY = [
    "께서는 오늘 방문했습니다.", "에게는 따로 안내했습니다.", "인데요.", "마저 불참했습니다.",
    "조차 몰랐습니다.", "뿐입니다.", "밖에 없습니다.",
]
# 받침이 있을 때 / 없을 때 모양이 달라지는 어미.
_ENDINGS_BY_BATCHIM = [
    ("이에요.", "예요."), ("이었습니다.", "였습니다."), ("이라고 합니다.", "라고 합니다."),
    ("이라는 분입니다.", "라는 분입니다."), ("이야.", "야."),
]


def gen_name_unlisted_ending(rng: random.Random) -> MissDoc:
    role = rng.choice(["담당자", "고객", "환자", "신청자", "학생", "보호자"])
    name = _name3(rng)
    if rng.random() < 0.5:
        # "고객 ○○○께서는 …" — 이름이 문장의 주어·대상이라 역할어에 조사를 붙이지 않는다.
        lead, ending = f"{role} ", rng.choice(_ENDINGS_ANY)
    else:
        # "담당자는 ○○○예요" — 이름을 소개하는 문장이라 역할어에 은/는이 붙기도 한다.
        lead = rng.choice([f"{role} ", f"{role}{_josa(role, '은', '는')} "])
        with_batchim, without = rng.choice(_ENDINGS_BY_BATCHIM)
        ending = _josa(name, with_batchim, without)
    return _build([lead, ("name", name), ending], "name_unlisted_ending", 600)


# ── #601 두 글자 이름 + 직함 ───────────────────────────────────────


def gen_name_two_syllable_title(rng: random.Random) -> MissDoc:
    name = _name2(rng)
    title = rng.choice(["팀장", "부장", "대표", "과장", "실장"])
    tail = rng.choice([
        f"{_josa(title, '이', '가')} 프로젝트 현황을 보고했습니다.",
        "님께 서류를 전달했습니다.",
        f"{_josa(title, '이', '가')} 계약서에 서명했습니다.",
    ])
    return _build([("name", name), f" {title}{tail}"], "name_two_syllable_title", 601)


# ── #602 라벨 뒤 나열한 이름 ───────────────────────────────────────


def gen_name_list_after_label(rng: random.Random) -> MissDoc:
    """첫 이름은 라벨이 단서라 지금도 잡힌다(target 아님). 둘째부터가 이 이슈의 대상이다."""
    label = rng.choice(["참석자", "담당자", "보호자", "수신인"])
    delimiter = rng.choice([", ", "·", " 및 ", " "])
    names = [_name3(rng) for _ in range(rng.choice([2, 3]))]
    parts: list[Part] = [f"{label}: ", ("name", names[0], False)]
    for name in names[1:]:
        parts += [delimiter, ("name", name)]
    return _build(parts, "name_list_after_label", 602)


# ── #603 단서 어휘 누락 ────────────────────────────────────────────

_ROLE_LABELS = [
    "작성: ", "서명: ", "발신: ", "결재: ", "받는 분: ", "구매자: ", "승인자: ",
    "검토자 ", "기안자 ", "주문자 ", "예약자 ", "피고인 ", "채무자 ", "세대주 ", "신고인 ", "보내는 사람 ",
]
_TITLES_AFTER = ["책임님", "선임", "수석님", "박사", "프로", "기사님", "선수", "여사"]
_CLOSINGS = ["귀하", "드림", "올림", "배상"]


def gen_name_cue_role_label(rng: random.Random) -> MissDoc:
    return _build([rng.choice(_ROLE_LABELS), ("name", _name3(rng))], "name_cue_role_label", 603)


def gen_name_cue_title_after(rng: random.Random) -> MissDoc:
    title = rng.choice(_TITLES_AFTER)
    return _build([("name", _name3(rng)), f" {title} 확인 부탁드립니다."], "name_cue_title_after", 603)


def gen_name_cue_closing(rng: random.Random) -> MissDoc:
    greeting = rng.choice(["감사합니다.\n", "이상입니다.\n", ""])
    return _build([greeting, ("name", _name3(rng)), f" {rng.choice(_CLOSINGS)}"], "name_cue_closing", 603)


# ── #604 이름 바로 뒤 괄호 ─────────────────────────────────────────


def gen_name_paren_after(rng: random.Random) -> MissDoc:
    age = rng.randint(20, 79)
    note = rng.choice([
        "(대리)", "(과장)", f"({age}세, {rng.choice('남여')})", f"(만 {age}세)", "(인)", " (서명)",
    ])
    return _build([("name", _name3(rng)), note], "name_paren_after", 604)


# ── #605 주소 꼬리(층·호·건물명) ───────────────────────────────────

# 지어낸 건물 이름. 접미어는 core의 건물명 목록(아파트·빌라·오피스텔·맨션·타워)에 없는 것만 쓴다.
_BUILDING_STEMS = ["한빛", "새솔", "가온", "누리", "다온"]


def gen_address_tail_floor_unit(rng: random.Random) -> MissDoc:
    floor = rng.randint(2, 20)
    tail = rng.choice([
        f" {floor}층 {floor}{rng.randint(1, 9):02d}호", f", {floor}층", f" 지하 {rng.randint(1, 3)}층", f" {floor}층",
    ])
    return _build(["주소: ", ("address", _base_address(rng) + tail)], "address_tail_floor_unit", 605)


def gen_address_tail_building(rng: random.Random) -> MissDoc:
    stem, floor = rng.choice(_BUILDING_STEMS), rng.randint(2, 20)
    tail = rng.choice([
        f" {stem}빌딩 {floor}층", f" {stem}센터 {floor}{rng.randint(1, 9):02d}호",
        f" {stem}스퀘어 {rng.choice('ABN')}동 {floor}층", f" {stem}프라자 {floor}층 {floor}{rng.randint(1, 9):02d}호",
    ])
    return _build(["주소: ", ("address", _base_address(rng) + tail)], "address_tail_building", 605)


def gen_address_tail_paren_dong(rng: random.Random) -> MissDoc:
    """도로명주소 뒤 참고항목 괄호 — "… 테헤란로 123 (역삼동)"."""
    gu, dong = rng.choice([pair.split() for pair in _GU_DONG if len(pair.split()) == 2])
    value = f"{rng.choice(_CITIES)} {gu} {rng.choice(_ROAD_ADDRESSES)} {rng.randint(1, 300)} ({dong})"
    return _build(["주소: ", ("address", value)], "address_tail_paren_dong", 605)


# ── #606 "시"를 뗀 시 이름으로 시작하는 주소 ───────────────────────

# 일반구가 있는 시와 그 구(공개된 행정구역 이름). 도로명·번지는 무작위로 붙인다.
_CITY_WITHOUT_SI = [
    ("수원", "영통구"), ("성남", "분당구"), ("고양", "일산동구"), ("용인", "기흥구"),
    ("안양", "동안구"), ("청주", "흥덕구"), ("천안", "서북구"), ("전주", "완산구"),
]


def gen_address_city_without_si(rng: random.Random) -> MissDoc:
    """단서가 없으면 통째로 놓치고, 단서가 있으면 구부터만 가려 시 이름이 남는다 — 둘 다 만든다."""
    city, gu = rng.choice(_CITY_WITHOUT_SI)
    value = f"{city} {gu} {rng.choice(_ROAD_ADDRESSES)} {rng.randint(1, 300)}"
    cue = rng.choice(["", "", "주소: ", "배송지 "])
    return _build([cue, ("address", value), rng.choice(["", "입니다."])], "address_city_without_si", 606)


# ── #607 라벨 + 검증 숫자가 틀린 번호 ──────────────────────────────


def _wrong_digit(digit: str, rng: random.Random) -> str:
    """맞는 검증 숫자에서 1~9를 더해 반드시 틀린 숫자를 만든다."""
    return str((int(digit) + rng.randint(1, 9)) % 10)


def gen_card_label_bad_checksum(rng: random.Random) -> MissDoc:
    payload = rng.choice(["4", "51", "52", "53", "54", "55"])
    payload += "".join(str(rng.randint(0, 9)) for _ in range(15 - len(payload)))
    digits = payload + _wrong_digit(_luhn_check_digit(payload), rng)
    value = "-".join(digits[i : i + 4] for i in range(0, 16, 4))
    label = rng.choice(["카드번호 ", "카드번호: ", "법인카드 ", "신용카드 번호: "])
    return _build([label, ("card", value)], "card_label_bad_checksum", 607)


def gen_biz_reg_label_bad_checksum(rng: random.Random) -> MissDoc:
    front9 = "".join(str(rng.randint(0 if i else 1, 9)) for i in range(len(_BIZ_REG_WEIGHTS)))
    digits = front9 + _wrong_digit(_biz_reg_check_digit(front9), rng)
    value = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    label = rng.choice(["사업자등록번호 ", "사업자등록번호: ", "사업자번호: "])
    return _build([label, ("biz_reg", value)], "biz_reg_label_bad_checksum", 607)


# ── #608 같은 문서에서 단서 없이 다시 나오는 이름 ──────────────────


def gen_name_repeat_without_cue(rng: random.Random) -> MissDoc:
    """첫 언급에만 단서가 있다(target 아님). 뒤 두 번은 이름만 나온다."""
    role = rng.choice(["담당자", "고객", "환자", "신청자"])
    name = _name3(rng)
    opening = rng.choice(["님이 문의했습니다. ", "님 건입니다. ", "입니다. "])
    return _build(
        [
            f"{role} ", ("name", name, False), opening,
            "어제 ", ("name", name), f"{_josa(name, '이', '가')} 서류를 제출했고, ",
            ("name", name), "의 연락처는 따로 받았습니다.",
        ],
        "name_repeat_without_cue",
        608,
    )


MISS_TAGS = {
    f.__name__: f
    for f in (
        gen_name_change_log_second,
        gen_birth_date_cue_after,
        gen_address_building_dong_ho_only,
        gen_driver_license_region_name,
        gen_name_unlisted_ending,
        gen_name_two_syllable_title,
        gen_name_list_after_label,
        gen_name_cue_role_label,
        gen_name_cue_title_after,
        gen_name_cue_closing,
        gen_name_paren_after,
        gen_address_tail_floor_unit,
        gen_address_tail_building,
        gen_address_tail_paren_dong,
        gen_address_city_without_si,
        gen_card_label_bad_checksum,
        gen_biz_reg_label_bad_checksum,
        gen_name_repeat_without_cue,
    )
}


def generate_open_misses_dataset(seed: int, per_tag: int = 20) -> list[dict]:
    """태그마다 per_tag건씩, 항상 같은 시드로 재현 가능하게 만든다(variants와 같은 방식)."""
    rows = []
    for name in sorted(MISS_TAGS):
        rng = random.Random(f"{seed}:{name}")
        for _ in range(per_tag):
            doc = MISS_TAGS[name](rng)
            rows.append({
                "text": doc.text,
                "labels": doc.labels,
                "difficulty": "open_miss",
                "miss_tag": doc.miss_tag,
                "issue": doc.issue,
            })
    return rows
