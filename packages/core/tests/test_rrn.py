# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""RRN 탐지기 테스트. 모든 번호는 합성(가짜)이다 — 진짜 개인정보 커밋 금지."""

import pytest

from maskingtape import Pipeline
from maskingtape.detectors import RRNDetector

# 체크섬까지 유효하게 계산해 만든 합성 번호 (실존 인물과 무관)
VALID_RRN = "800101-1234560"
# 형식·날짜는 맞지만 체크섬이 틀린 합성 번호 (2020-10 이후 발급분 시나리오)
NO_CHECKSUM_RRN = "800101-1234567"


def test_detects_valid_rrn():
    found = RRNDetector().detect(f"주민번호는 {VALID_RRN} 입니다")
    assert len(found) == 1
    assert found[0].kind == "rrn"
    assert found[0].text == VALID_RRN
    assert found[0].confidence == 1.0


def test_checksum_mismatch_lowers_confidence_only():
    # 체크섬 불일치는 탈락이 아니라 확신도만 낮춘다 (2020-10 이후 발급분은 체크섬 없음)
    found = RRNDetector().detect(NO_CHECKSUM_RRN)
    assert len(found) == 1
    assert found[0].confidence < 1.0


def test_detects_without_separator():
    found = RRNDetector().detect("8001011234560")
    assert len(found) == 1
    assert found[0].confidence == 1.0


def test_detects_with_dot_separator():
    # 점(.)으로 구분한 서식도 잡아야 한다 (미탐=유출) — 앞 6자리와 뒤 7자리는 VALID_RRN과 동일
    found = RRNDetector().detect("주민번호 800101.1234560")
    assert len(found) == 1
    assert found[0].text == "800101.1234560"
    assert found[0].confidence == 1.0


def test_detects_separator_variants_that_previously_leaked():
    # 미탐=유출: Word/HWP 자동서식(en-dash)·표 붙여넣기(공백-하이픈-공백·이중공백)에서
    # 주민번호가 통째로 새던 문제. 앞 6자리·뒤 7자리는 VALID_RRN과 동일하므로 확신도 1.0.
    for variant in (
        "주민 800101 - 1234560 확인",  # 공백-하이픈-공백
        "주민 800101  1234560 확인",  # 이중 공백
        "주민 800101–1234560 확인",  # en-dash(–)
        "주민 800101—1234560 확인",  # em-dash(—)
        "주민 800101. 1234560 확인",  # 점 + 공백
    ):
        found = RRNDetector().detect(variant)
        assert len(found) == 1, variant
        assert found[0].confidence == 1.0, variant


def test_rejects_impossible_birthdate():
    # 13월 32일은 날짜가 아니므로 탐지하면 안 된다
    assert RRNDetector().detect("991332-1234567") == []


def test_rejects_longer_digit_runs():
    # 앞뒤로 숫자가 더 붙은 긴 수열(계좌번호 등)은 주민번호가 아니다
    assert RRNDetector().detect("98001011234560123") == []


# ── 뒷자리를 가린 표기(#528) ────────────────────────────────────────
# 문서에는 주민등록번호 뒷자리 일부만 가려 적는 경우가 많다("800101-1******"). 뒷자리가
# 숫자 7개일 때만 잡던 예전 정규식은 이 표기를 통째로 놓쳤다 — 남은 앞 6(또는 8)자리와
# 성별 숫자만으로도 생년월일·성별이 드러나므로 미탐은 곧 유출이다.


def test_masked_tail_with_asterisks_is_still_an_rrn():
    found = RRNDetector().detect("주민번호 800101-1******")
    assert len(found) == 1
    assert found[0].kind == "rrn"
    assert found[0].text == "800101-1******"
    assert found[0].confidence == 0.85  # 뒷자리가 가려져 체크섬을 계산할 수 없다


def test_masked_tail_with_capital_x_is_still_an_rrn():
    found = RRNDetector().detect("주민번호 800101-1XXXXXX")
    assert len(found) == 1
    assert found[0].text == "800101-1XXXXXX"


def test_masked_tail_with_circle_char_and_different_gender_code():
    found = RRNDetector().detect("주민등록번호: 800101-2●●●●●●")
    assert len(found) == 1
    assert found[0].text == "800101-2●●●●●●"


def test_eight_digit_front_with_masked_tail_is_still_an_rrn():
    # 8자리 앞자리(#508)와 가려진 뒷자리(#528)가 함께 와도 잡아야 한다
    found = RRNDetector().detect("생년월일 19800101-1******")
    assert len(found) == 1
    assert found[0].text == "19800101-1******"
    assert found[0].kind == "rrn"


def test_gender_digit_alone_with_no_tail_is_still_an_rrn():
    # 뒷자리를 아예 안 적고 성별 숫자만 남은 표기도 앞자리(생년월일)가 새는 걸 막아야 한다
    found = RRNDetector().detect("생년월일 19800101-1")
    assert len(found) == 1
    assert found[0].text == "19800101-1"


def test_partial_back_with_a_few_real_digits_and_masks_is_still_an_rrn():
    # 뒷자리 일부만 적고 나머지를 가린 표기(#637) — 생년월일 날짜와 남은 숫자가 모두 가려져야 한다
    found = RRNDetector().detect("생년월일 19800101-1234***")
    assert len(found) == 1
    assert found[0].text == "19800101-1234***"
    assert found[0].confidence == 0.85


def test_short_real_back_digits_after_a_date_are_still_an_rrn():
    found = RRNDetector().detect("생년월일 19800101-12 기재")
    assert len(found) == 1
    assert found[0].text == "19800101-12"


def test_six_digit_front_with_a_partial_back_is_still_an_rrn():
    found = RRNDetector().detect("생년월일 800101-1234***")
    assert len(found) == 1
    assert found[0].text == "800101-1234***"


def test_bare_gender_digit_without_any_separator_context_is_not_falsely_grabbed():
    # 구분자 없이 붙여 쓴 "800101" 뒤에 성별 숫자로 보일 법한 숫자 하나만 있고 더 이어지면
    # (예: 전화번호 뒷자리 일부) 오탐하지 않는다 — 뒤에 숫자가 더 있으므로 경계에서 걸러진다
    assert RRNDetector().detect("800101 1234") == []


# ── 드문 구분자·날짜 표기(#529, #508 독립 검증) ──────────────────────
# 앞자리·뒷자리 사이 구분자가 하이픈·점·공백 계열 밖이면(슬래시·밑줄·가운뎃점 등) 원문
# 그대로 샜다. 앞자리를 점·하이픈으로 나눠 쓴 날짜 표기(#529) 뒤에 뒷자리가 이어지는
# 경우도 마찬가지였다.


@pytest.mark.parametrize(
    "sep",
    ["/", "·", "_", " -  ", ",", ":", "ㆍ", "‧", "~", "|"],
)
def test_rare_separators_between_front_and_back_are_masked(sep):
    text = f"주민번호 800101{sep}1234567"
    found = RRNDetector().detect(text)
    assert len(found) == 1, f"구분자 {sep!r}에서 못 잡음: {text!r}"
    assert found[0].text == f"800101{sep}1234567"


@pytest.mark.parametrize(
    "front",
    ["1980.01.01", "1980-01-01"],
)
def test_dotted_or_hyphenated_date_front_with_a_back_is_an_rrn(front):
    # "1980.01.01-1234567"처럼 점·하이픈으로 나눠 쓴 생년월일 뒤에 뒷자리가 이어지면
    # 그 자체로 주민등록번호다 — 날짜 표기만 보고 뒷자리를 놓치면 뒷자리 7개가 통째로 샌다.
    text = f"생년월일 {front}-1234567"
    found = RRNDetector().detect(text)
    assert len(found) == 1, f"{front} 케이스를 못 잡음: {text!r}"
    assert found[0].text == f"{front}-1234567"


def test_dotted_date_front_checksum_uses_two_digit_year():
    # 체크섬은 YYMMDD 6자리를 쓴다 — "1980.01.01"의 4자리 연도가 아니라 뒤 2자리("80")로
    # 계산해야 한다. VALID_RRN("800101-1234560")과 앞 6자리가 같은 값으로 검증한다.
    found = RRNDetector().detect("1980.01.01-1234560")
    assert len(found) == 1
    assert found[0].confidence == 1.0


def test_pure_slash_date_without_a_back_is_not_falsely_grabbed():
    # 대조군: 순수 날짜 표기("1999/07/21")는 뒷자리 모양이 없으므로 주민등록번호가 아니다 —
    # 구분자를 슬래시까지 넓히면서 평범한 날짜까지 오탐하면 안 된다.
    assert RRNDetector().detect("1999/07/21") == []


# ── 가운뎃점과 닮은 점 문자(#631) ─────────────────────────────────────
# 가운뎃점(·, ㆍ, ‧)은 #529로 받았지만 모양이 비슷한 다른 점 문자는 구분자 목록에도 입력
# 정규화에도 없어 번호가 통째로 샜다. "생년월일" 뒤에서는 생년월일 탐지기가 앞 6자리만 잡아
# 뒷자리 7개가 남았다. 눈으로 헷갈리므로 코드값으로 만든다.

_DOT_LIKE_CODEPOINTS = [
    0x30FB,  # 가타카나 가운뎃점
    0xFF65,  # 반각 가타카나 가운뎃점
    0x2022,  # 글머리 기호
    0x2219,  # 글머리 연산자
    0x22C5,  # 점 연산자
    0x2024,  # 한 점 리더
    0xFE52,  # 작은 마침표
    0x2981,  # Z 표기 점
    0x25CF,  # 검은 동그라미
    0x00B8,  # 세딜라
    0x02D9,  # 윗점
]


@pytest.mark.parametrize("codepoint", _DOT_LIKE_CODEPOINTS, ids=lambda c: f"U+{c:04X}")
@pytest.mark.parametrize("prefix", ["주민번호 ", "생년월일 ", ""], ids=["rrn-label", "birth-label", "bare"])
def test_dot_like_separators_mask_the_whole_number(prefix, codepoint):
    number = f"800101{chr(codepoint)}1234560"
    text = prefix + number
    assert [(d.kind, d.text) for d in Pipeline().scan(text)] == [("rrn", number)], text
    assert Pipeline().anonymize(text).text == prefix + "*" * len(number)


@pytest.mark.parametrize("sep", ["/", "·", "ㆍ", "‧", "~", "|", chr(0x30FB), chr(0x2022)])
def test_birth_label_hands_a_checksumless_number_to_rrn(sep):
    # 체크섬이 없는 번호(2020-10 이후 발급분)는 확신도가 0.85라, 생년월일 탐지기(0.9)가 앞
    # 6자리를 잡으면 종류가 생년월일로 바뀌었다(#529 구분자부터 그랬다). 생년월일 쪽이 주민등록번호
    # 탐지기와 같은 구분자 판정(RRN_BACK_AHEAD)을 쓰므로 이제 주민등록번호로 남는다.
    number = f"800101{sep}1234567"
    assert [(d.kind, d.text) for d in Pipeline().scan(f"생년월일 {number}")] == [("rrn", number)]


def test_bullets_around_dates_are_not_grabbed():
    # 대조군: 글머리 기호로 시작하는 날짜 목록은 뒷자리 모양이 없으므로 주민등록번호가 아니다.
    text = f"{chr(0x2022)} 2024.01.01 회의\n{chr(0x2022)} 2024.01.02 보고"
    assert Pipeline().scan(text) == []


# ── 가려지거나 성별 숫자만 남은 뒷자리는 하이픈류 구분자일 때만(#528 후속) ──
# 리뷰(팀장, PR #564)에서 찾은 오탐: 구분자를 요구하지 않으면(공백이나 아예 없어도 됨)
# 날짜로 시작하는 무관한 숫자열까지 주민번호로 잡는다. 완전한 숫자 7개짜리 뒷자리는
# 기존처럼 느슨한 구분자(공백·하이픈·점 등)를 허용하되, 가려지거나 성별 숫자만 남은
# 뒷자리는 하이픈류 문자가 실제로 있을 때만 받는다.


@pytest.mark.parametrize(
    "text",
    [
        "주문번호 9912315",  # 임의 7자리 숫자
        "주문번호 2409305",  # 날짜로 시작하는 7자리 숫자
        "작성일 240101 3건",  # 날짜 + 공백 + 건수(성별 숫자로 오인되기 쉬움)
        "사원번호: 8501012",
        "재고 코드 1203155",
    ],
)
def test_date_like_numbers_without_a_hyphen_are_not_falsely_grabbed(text):
    assert RRNDetector().detect(text) == [], text


def test_masked_tail_still_needs_a_real_hyphen_like_separator():
    # 성별 숫자만 남은 뒷자리 앞에 공백만 있고 하이픈류 문자가 없으면 더는 안 받는다 —
    # 위 "작성일 240101 3건"과 같은 이유다.
    assert RRNDetector().detect("생년월일 800101 1") == []


def test_full_seven_digit_back_with_a_loose_separator_is_still_masked():
    # 완전한 숫자 7개 뒷자리는 공백처럼 느슨한 구분자를 그대로 허용한다(#528 후속에서도
    # 회귀 없음 — 위 항목들과 다른 갈래(_BACK)를 타므로 영향받지 않는다).
    found = RRNDetector().detect("800101 1234567")
    assert len(found) == 1
    assert found[0].text == "800101 1234567"


# ── 날짜 앞자리를 다른 꼴로 쓰고 뒷자리를 이어 쓴 표기(#638) ─────────────────────
# 생년월일 탐지기는 날짜만 가리고, 주민번호 탐지기는 2자리 연도·슬래시·한 자리 월일·한글 날짜
# 앞자리를 받지 않아 뒷자리 7개가 샜다.


def test_two_digit_year_dotted_front_with_a_full_back_is_still_an_rrn():
    found = RRNDetector().detect("생년월일 80.01.01-1234567")
    assert len(found) == 1
    assert found[0].text == "80.01.01-1234567"


def test_slash_separated_front_with_a_full_back_is_still_an_rrn():
    found = RRNDetector().detect("생년월일 1980/01/01-1234567")
    assert len(found) == 1
    assert found[0].text == "1980/01/01-1234567"


def test_single_digit_month_and_day_front_with_a_full_back_is_still_an_rrn():
    found = RRNDetector().detect("생년월일 1980.1.1-1234567")
    assert len(found) == 1
    assert found[0].text == "1980.1.1-1234567"


def test_korean_date_front_with_a_full_back_is_still_an_rrn():
    found = RRNDetector().detect("생년월일 1980년 1월 1일-1234567")
    assert len(found) == 1
    assert found[0].text == "1980년 1월 1일-1234567"


def test_dated_front_that_is_not_a_real_date_is_still_rejected():
    assert RRNDetector().detect("주문번호 2024.13.45-1234567") == []


# ── 뒷자리 바로 뒤에 영문 한 글자가 붙은 표기(#640) ─────────────────────────
# 뒷자리 경계를 (?![\dA-Za-z])로 두면 "800101-1234560A"처럼 뒤에 영문 한 글자가 붙은 번호가
# 통째로 샜다. 영문 한 글자 뒤에 영숫자가 더 이어지는 긴 코드는 여전히 받지 않는다.


def test_full_back_followed_by_one_english_letter_is_still_an_rrn():
    found = RRNDetector().detect("800101-1234567A")
    assert len(found) == 1
    assert found[0].text == "800101-1234567A"


def test_valid_checksum_with_trailing_letter_keeps_full_confidence():
    found = RRNDetector().detect("주민번호 800101-1234560A")
    assert len(found) == 1
    assert found[0].text == "800101-1234560A"
    assert found[0].confidence == 1.0


def test_trailing_letter_followed_by_more_alphanumerics_is_still_not_an_rrn():
    # 영문이 두 글자 이상 이어지는 영숫자 코드는 주민번호가 아니다(오탐 방지)
    assert RRNDetector().detect("주문번호 800101-1234560AB") == []
    assert RRNDetector().detect("800101-1234560A1") == []


def test_trailing_letter_followed_by_a_hyphenated_code_is_not_an_rrn():
    # "…-B" 같은 하이픈 이어짐은 주민번호 뒤의 다른 코드 조각이므로 받지 않는다
    assert RRNDetector().detect("운송장 800101-1234560A-B") == []


def test_short_unmasked_digits_after_a_six_digit_date_are_not_an_rrn():
    # "240101-1234"처럼 6자리 날짜 뒤에 일련번호가 짧게 붙은 것은 주문·운송장 번호에 흔하다 — 가림
    # 문자가 없으면 8자리 생년월일 앞자리일 때만 뒷자리 일부를 받는다(#637 오탐 방지)
    assert RRNDetector().detect("운송장 240101-12345") == []
    assert RRNDetector().detect("제품 240101-1234 입고") == []
    assert RRNDetector().detect("주문번호 2024-01-01-12") == []


def test_short_digits_after_an_order_number_date_are_not_an_rrn_without_a_label():
    # "ORD-20250408-2110"처럼 8자리 날짜형 주문번호의 짧은 일련번호는 주민번호 라벨이 없으면 받지 않는다
    assert RRNDetector().detect("주문번호 ORD-20250408-2110") == []


# ── #637 후속: 머지 후 재측정에서 남은 모양(서연님 10/5 댓글) ─────────────────────
# 셋 다 주민번호·생년월일 라벨이 앞에 있을 때만 받는다 — 라벨 없는 날짜형 주문번호 오탐 방지.


def test_six_digit_front_with_short_digits_after_a_label_is_an_rrn():
    found = RRNDetector().detect("주민번호 030123-45 기재")
    assert len(found) == 1
    assert found[0].text == "030123-45"


def test_spaced_dotted_date_front_with_trailing_dot_is_an_rrn():
    found = RRNDetector().detect("생년월일 1980. 1. 1.-1234567")
    assert len(found) == 1
    assert found[0].text == "1980. 1. 1.-1234567"


def test_back_with_one_inner_space_after_a_label_is_an_rrn():
    found = RRNDetector().detect("주민번호 800101 - 1234 567")
    assert len(found) == 1
    assert found[0].text == "800101 - 1234 567"


def test_followup_shapes_without_a_label_are_still_not_an_rrn():
    assert RRNDetector().detect("주문 030123-45 처리") == []
    assert RRNDetector().detect("코드 800101 - 1234 567") == []


def test_gender_digit_followed_by_spaced_digits_without_a_label_keeps_the_old_partial_match():
    # 공백 낀 뒷자리 갈래가 라벨이 없어 버려져도 전에 잡던 "800101-1"은 그대로 잡는다(덜 가림 방지)
    assert [d.text for d in RRNDetector().detect("800101-1 234567")] == ["800101-1"]
