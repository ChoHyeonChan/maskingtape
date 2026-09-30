# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""표기 변형 평가 세트(#531) — 9/28 전수 감사 뒤로 core가 새로 막은 표기를 정답 라벨로 재서,
벤치 점수에 안 보이는 개선을 숫자로 보인다.

핵심 전제(이슈 본문): 이 세트는 core 테스트(test_address_spacing.py/test_name_forms.py/
test_normalize.py/test_common_forms.py)와 **같은 모양**을 새로 쓴 합성 문장이다 — 테스트
문장을 그대로 복사하지 않는다. 값은 매번 새로 뽑고(재현 가능하도록 시드만 고정), 문장의
틀(단서·구분자·자리 배치)만 core 테스트가 다룬 표기를 따른다.

각 항목은 `variant_tag`로 표기 종류를 구분해, 종류별 재현율을 따로 볼 수 있게 한다. 이
세트는 "우리가 찾아서 고친 표기"로 만들어 우리에게 유리하다 — 일반 정확도가 아니라
"알려진 누출을 막았는지 보는 회귀 지표"로만 쓴다(README에도 이 한계를 그대로 적는다).
"""

from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass

from bench.generator.entities import (
    _CENTURY_CODES,
    _CITIES,
    _FOREIGN_CENTURY_CODES,
    _GIVEN_SYLLABLES,
    _GU_DONG,
    _GU_NAMES,
    _ROAD_ADDRESSES,
    _RRN_WEIGHTS,
    _SURNAMES,
    _luhn_check_digit,
)

NBSP, IDEO_SPACE, ZWSP, SHY = chr(0xA0), chr(0x3000), chr(0x200B), chr(0xAD)
EN_DASH, MINUS, FW_HYPHEN = chr(0x2013), chr(0x2212), chr(0xFF0D)
HANGUL_FILLER = chr(0x3164)


@dataclass(frozen=True)
class VariantDoc:
    text: str
    labels: list[dict]
    variant_tag: str


def _fullwidth(text: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in text)


def _gen_name(rng: random.Random) -> str:
    return rng.choice(_SURNAMES) + "".join(rng.sample(_GIVEN_SYLLABLES, k=rng.choice([1, 2])))


def _gen_name_long(rng: random.Random) -> str:
    """성+2음절 이름(3음절 전체) — core 테스트가 이 표기들에서 항상 쓴 길이. 2음절
    이름(성+1음절)은 core에 별도의 알려진 한계(#255/#491)가 있어, 섞으면 "표기 자체를
    새로 잡는지"와 "짧은 이름을 잡는지"가 뒤섞여 이 태그의 재현율을 왜곡한다."""
    return rng.choice(_SURNAMES) + "".join(rng.sample(_GIVEN_SYLLABLES, k=2))


def _gen_rrn_digits(rng: random.Random) -> str:
    century = rng.choice([1900, 2000])
    year, month, day = rng.randint(0, 99), rng.randint(1, 12), rng.randint(1, 28)
    century_code = rng.choice(_CENTURY_CODES[century] if rng.random() < 0.85 else _FOREIGN_CENTURY_CODES[century])
    front = f"{year:02d}{month:02d}{day:02d}"
    serial = f"{rng.randint(0, 99999):05d}"
    digits = front + century_code + serial
    check = (11 - sum(int(d) * w for d, w in zip(digits, _RRN_WEIGHTS)) % 11) % 10
    return f"{front}{century_code}{serial}{check}"


def _gen_phone_digits(rng: random.Random, mobile: bool = True) -> tuple[str, str, str]:
    """(지역/식별번호, 국번, 가입자번호) 세 자리 묶음을 돌려준다."""
    if mobile:
        return "010", f"{rng.randint(1000, 9999)}", f"{rng.randint(1000, 9999)}"
    area = rng.choice(["02", "031", "051"])
    mid = f"{rng.randint(100, 999)}" if area != "02" else f"{rng.randint(1000, 9999)}"
    return area, mid, f"{rng.randint(1000, 9999)}"


def _wrap(cue: str, value: str, tail: str, tag: str, kind: str) -> VariantDoc:
    text = cue + value + tail
    start = len(cue)
    end = start + len(value)
    return VariantDoc(text=text, labels=[{"kind": kind, "start": start, "end": end}], variant_tag=tag)


# ── 주소(#492) ──────────────────────────────────────────────────────


def gen_address_wide_spaces(rng: random.Random) -> VariantDoc:
    city, gu_dong = rng.choice(_CITIES), rng.choice(_GU_DONG)
    road, num = rng.choice(_ROAD_ADDRESSES), rng.randint(1, 200)
    gap = rng.choice(["  ", "   ", "\t", "\t\t"])
    value = f"{city}{gap}{gu_dong.split()[0]}{gap}{road}{gap}{num}"
    return _wrap("주소: ", value, " 입니다.", "address_wide_spaces", "address")


def gen_address_gu_start(rng: random.Random) -> VariantDoc:
    cue = rng.choice(["주소: ", "배송지 ", "거주지: ", "사업장 소재지 "])
    gu, road, num = rng.choice(_GU_NAMES), rng.choice(_ROAD_ADDRESSES), rng.randint(1, 200)
    value = f"{gu} {road} {num}"
    return _wrap(cue, value, "입니다.", "address_gu_start", "address")


# ── 이름(#491) ──────────────────────────────────────────────────────


def gen_name_form_colon(rng: random.Random) -> VariantDoc:
    label = rng.choice(["성명", "이름", "예금주", "성함"])
    sep = rng.choice([" : ", ": ", " :  ", "\t:\t"])
    name = _gen_name(rng)
    return _wrap(f"{label}{sep}", name, "", "name_form_colon", "name")


def gen_name_form_table(rng: random.Random) -> VariantDoc:
    label = rng.choice(["성명", "이름", "고객"])
    name = _gen_name(rng)
    text = f"| {label} | {name} |"
    start = text.index(name)
    return VariantDoc(text=text, labels=[{"kind": "name", "start": start, "end": start + len(name)}], variant_tag="name_form_table")


def gen_name_form_paren_label(rng: random.Random) -> VariantDoc:
    label, note = rng.choice([("성명", "한글"), ("신청인", "대표자")])
    name = _gen_name(rng)
    return _wrap(f"{label}({note}): ", name, "", "name_form_paren_label", "name")


def gen_name_title_particle(rng: random.Random) -> VariantDoc:
    role_cue = rng.choice(["고객", "담당자", "환자", "신청자"])
    title_particle = rng.choice(["원장이", "차장은", "주임이", "원장은"])
    name = _gen_name_long(rng)
    return _wrap(f"{role_cue} : {title_particle} ", name, "입니다", "name_title_particle", "name")


def gen_name_paren_after_label(rng: random.Random) -> VariantDoc:
    label = rng.choice(["담당자", "신청인", "고객", "학생"])
    title = rng.choice(["대리", "과장", "군", "님"])
    name = _gen_name_long(rng)
    return _wrap(f"{label}(", name, f" {title}) 문의", "name_paren_after_label", "name")


# ── 표기 정리(#490) ─────────────────────────────────────────────────


def gen_fullwidth_rrn(rng: random.Random) -> VariantDoc:
    digits = _gen_rrn_digits(rng)
    value = f"{digits[:6]}-{digits[6:]}"
    return _wrap("주민번호 ", _fullwidth(value), "", "fullwidth", "rrn")


def gen_nfd_name(rng: random.Random) -> VariantDoc:
    name = _gen_name(rng)
    nfd_name = unicodedata.normalize("NFD", name)
    return _wrap("고객 ", nfd_name, "님 문의", "nfd_hangul", "name")


def gen_invisible_chars_phone(rng: random.Random) -> VariantDoc:
    area, mid, last = _gen_phone_digits(rng)
    value = f"{area}-{mid}{ZWSP}-{last}"
    return _wrap("전화 ", value, "", "invisible_chars", "phone")


def gen_dash_variant_account(rng: random.Random) -> VariantDoc:
    sep = rng.choice([EN_DASH, MINUS, FW_HYPHEN])
    groups = [f"{rng.randint(0, 999):03d}", f"{rng.randint(0, 999):03d}", f"{rng.randint(0, 999999):06d}"]
    value = sep.join(groups)
    return _wrap("입금 계좌 ", value, "", "dash_variants", "account")


def gen_hangul_filler_address(rng: random.Random) -> VariantDoc:
    city, gu_dong = rng.choice(_CITIES), rng.choice(_GU_DONG)
    num = rng.randint(1, 200)
    value = f"{city}{HANGUL_FILLER}{gu_dong.split()[0]}{HANGUL_FILLER}{gu_dong.split()[1]}{HANGUL_FILLER}{num}"
    return _wrap("주소" + HANGUL_FILLER, value, "", "hangul_filler", "address")


# ── 흔한 표기(#493) ─────────────────────────────────────────────────


def gen_birthdate_dotted(rng: random.Random) -> VariantDoc:
    year, month, day = rng.randint(1950, 2010), rng.randint(1, 12), rng.randint(1, 28)
    value = f"{year}. {month}. {day}."
    return _wrap("생년월일: ", value, "", "birthdate_forms", "birth_date")


def gen_birthdate_compact(rng: random.Random) -> VariantDoc:
    year, month, day = rng.randint(1950, 2010), rng.randint(1, 12), rng.randint(1, 28)
    value = f"{year}{month:02d}{day:02d}"
    return _wrap("생년월일: ", value, "", "birthdate_forms", "birth_date")


def gen_birthdate_two_digit_year(rng: random.Random) -> VariantDoc:
    year, month, day = rng.randint(0, 99), rng.randint(1, 12), rng.randint(1, 28)
    value = f"{year:02d}년 {month}월 {day}일"
    return _wrap("생년월일: ", value, "", "birthdate_forms", "birth_date")


def gen_phone_area_parens(rng: random.Random) -> VariantDoc:
    area = rng.choice(["02", "031", "051"])
    mid = rng.randint(100, 999) if area != "02" else rng.randint(1000, 9999)
    value = f"{area}){mid}-{rng.randint(1000, 9999)}"
    return _wrap(rng.choice(["TEL ", "대표 "]), value, "", "phone_forms", "phone")


def gen_phone_intl_spaced(rng: random.Random) -> VariantDoc:
    area = rng.choice(["2", "31", "51"])
    value = f"+82 {area} {rng.randint(100, 999)} {rng.randint(1000, 9999)}"
    return _wrap("전화 ", value, "", "phone_forms", "phone")


def gen_account_attached_hyphen(rng: random.Random) -> VariantDoc:
    groups = [f"{rng.randint(0, 999):03d}", f"{rng.randint(0, 999):03d}", f"{rng.randint(0, 999999):06d}"]
    value = "-".join(groups)
    return _wrap("입금계좌-", value, "", "account_attached_hyphen", "account")


def gen_card_mixed_grouping(rng: random.Random) -> VariantDoc:
    """core의 카드 정규식은 4-4-4-4(16자리) 등 정해진 그룹 모양만 받는다(#493) — 구분자는
    하나로 반복돼야 하는 일반 모양과 달리, "하이픈·공백 섞어 쓴 16자리"만 별도 정규식
    (`_MIXED_CARD_RE`)으로 받으므로 그 모양을 그대로 따른다."""
    payload = "".join(f"{rng.randint(0, 9999):04d}" for _ in range(3)) + f"{rng.randint(0, 999):03d}"
    check = _luhn_check_digit(payload)
    digits = payload + check
    groups = [digits[0:4], digits[4:8], digits[8:12], digits[12:16]]
    seps = [rng.choice(["-", " "]) for _ in range(3)]
    value = groups[0] + seps[0] + groups[1] + seps[1] + groups[2] + seps[2] + groups[3]
    return _wrap("카드 ", value, "", "card_forms", "card")


def gen_passport_spaced(rng: random.Random) -> VariantDoc:
    letter = rng.choice("MDR")
    number = rng.randint(10_000_000, 99_999_999)
    value = f"{letter} {number}"
    return _wrap("여권번호 ", value, "", "passport_forms", "passport")


VARIANT_TAGS: dict[str, list] = {}
for _fn in (
    gen_address_wide_spaces,
    gen_address_gu_start,
    gen_name_form_colon,
    gen_name_form_table,
    gen_name_form_paren_label,
    gen_name_title_particle,
    gen_name_paren_after_label,
    gen_fullwidth_rrn,
    gen_nfd_name,
    gen_invisible_chars_phone,
    gen_dash_variant_account,
    gen_hangul_filler_address,
    gen_birthdate_dotted,
    gen_birthdate_compact,
    gen_birthdate_two_digit_year,
    gen_phone_area_parens,
    gen_phone_intl_spaced,
    gen_account_attached_hyphen,
    gen_card_mixed_grouping,
    gen_passport_spaced,
):
    VARIANT_TAGS[_fn.__name__] = _fn


def generate_variants_dataset(seed: int, per_tag: int = 15) -> list[dict]:
    """태그마다 per_tag건씩, 항상 같은 시드로 재현 가능하게 만든다."""
    rows = []
    for name in sorted(VARIANT_TAGS):
        gen = VARIANT_TAGS[name]
        rng = random.Random(f"{seed}:{name}")
        for _ in range(per_tag):
            doc = gen(rng)
            rows.append({"text": doc.text, "labels": doc.labels, "difficulty": "variant", "variant_tag": doc.variant_tag})
    return rows
