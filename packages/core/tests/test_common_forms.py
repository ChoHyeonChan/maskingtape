# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""생년월일·전화·계좌·카드·여권의 흔한 표기(#493) 테스트 — 전부 합성 값."""

import pytest

from maskingtape import Pipeline
from maskingtape.detectors import (
    AccountDetector,
    BirthDateDetector,
    CreditCardDetector,
    PassportDetector,
    PhoneDetector,
)


def texts(detector, text: str) -> list[str]:
    return [d.text for d in detector.detect(text)]


def assert_masked(text: str, value: str) -> None:
    start = text.index(value)
    end = start + len(value)
    masked = Pipeline().anonymize(text).text
    assert masked[start:end] == "*" * (end - start), masked


# ── 생년월일 ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, value",
    [
        ("생년월일: 1999. 7. 21.", "1999. 7. 21."),  # 공문서 날짜 표기
        ("생년월일: 1999 - 07 - 21", "1999 - 07 - 21"),
        ("생년월일: 19990721", "19990721"),
        ("생년월일 990721", "990721"),
        ("생년월일: 99년 7월 21일", "99년 7월 21일"),
        ("| 생년월일 | 1999-07-21 |", "1999-07-21"),
        ("생년월일(YYYY-MM-DD): 1999-07-21", "1999-07-21"),
        ("출생: 1999-07-21", "1999-07-21"),
        ("생년: 1999.07.21", "1999.07.21"),
    ],
)
def test_birthdate_forms(text, value):
    assert value in texts(BirthDateDetector(), text)


@pytest.mark.parametrize(
    "text",
    [
        "생년월일: 19991341",  # 13월
        "생년월일 991332",
        "출생 신고는 2026년에 했다",  # 날짜가 아니다
        "생년월일: 12345678901",  # 더 긴 숫자열
    ],
)
def test_birthdate_forms_need_a_real_date(text):
    assert BirthDateDetector().detect(text) == []


@pytest.mark.parametrize(
    "text, value",
    [
        # 라벨 뒤 괄호가 안쪽의 다른 라벨+날짜를 삼키던 회귀(#493 독립 검증)
        ("생일(음력 생일 1999.6.8) 1999.7.21", "1999.6.8"),
        ("출생(생일: 1999-07-21) 12345678", "1999-07-21"),
    ],
)
def test_birthdate_inside_parentheses_is_still_found(text, value):
    assert_masked(text, value)


@pytest.mark.parametrize("separator", ["-", " ", "  ", chr(0x2013), " - ", "\t"])
def test_compact_date_before_the_rrn_back_is_the_rrn_front(separator):
    # 체크섬이 안 맞는 주민번호(2020년 10월 이후 번호 대부분)는 확신도가 생년월일보다 낮다. 앞 6자리를
    # 생년월일로 잡으면 합친 구간의 종류가 주민번호에서 생년월일로 바뀐다(#493 독립 검증)
    kinds = {d.kind for d in Pipeline().scan("생년월일 800101" + separator + "1234567")}
    assert kinds == {"rrn"}


@pytest.mark.parametrize(
    "text, value",
    [
        ("생년월일 19800101-1234567", "19800101-1234567"),
        ("주민번호 19800101-1234567", "19800101-1234567"),  # 라벨과 상관없이 샌다
        ("19800101-1234567", "19800101-1234567"),
        ("주민등록번호: 19800101-1234560", "19800101-1234560"),  # 체크섬이 맞는 번호
        ("생년월일 20050101-3234567", "20050101-3234567"),  # 2000년대 출생
    ],
)
def test_eight_digit_front_with_the_rrn_back_is_an_rrn(text, value):
    # 8자리 생년월일 뒤에 뒷자리 7개가 붙으면 주민등록번호다. 구간 전체를 가리고 종류는 rrn으로 보고한다(#508)
    assert_masked(text, value)
    assert {d.kind for d in Pipeline().scan(text)} == {"rrn"}


@pytest.mark.parametrize("separator", [" ", ".", "  ", chr(0x2013), " - ", "\t"])
def test_eight_digit_front_is_not_taken_as_a_birthdate_before_the_rrn_back(separator):
    # 공백·점으로 나누면 8자리를 생년월일로 먼저 잡고 뒷자리 7개가 샜다. 6자리 앞자리와 같은 이유로
    # 생년월일로 잡으면 안 된다(#493 test_compact_date_before_the_rrn_back_is_the_rrn_front, #508)
    text = "생년월일 19800101" + separator + "1234567"
    assert_masked(text, "19800101" + separator + "1234567")
    assert {d.kind for d in Pipeline().scan(text)} == {"rrn"}


def test_eight_digit_front_is_kept_even_when_the_century_does_not_match():
    # 앞 두 자리(19)와 성별코드(3 = 2000년대)가 안 맞아도 버리지 않는다. 버리면 덜 가리게 된다(#508)
    assert_masked("주민번호 19050101-3234567", "19050101-3234567")


@pytest.mark.parametrize(
    "text, value",
    [
        ("생년월일 20000229 1234567", "20000229 1234567"),
        ("생년월일 000229 1234567", "000229 1234567"),  # 6자리도 같은 이유로 통째로 샜다
    ],
)
def test_leap_day_front_is_masked_whatever_the_gender_code_says(text, value):
    # 생년월일 탐지기는 뒤에 뒷자리가 오는 날짜를 주민번호에 넘긴다. 주민번호가 성별코드 1을 1900년대로만
    # 보고 1900년 2월 29일(없는 날짜)이라며 버리면 두 탐지기 모두 버려서 통째로 샌다(#508)
    assert_masked(text, value)


@pytest.mark.parametrize(
    "text, date",
    [
        ("생년월일 18991231 1234567", "18991231"),
        ("생년월일 21000101 1234567", "21000101"),
        ("생일 18800515.2345678", "18800515"),
    ],
)
def test_eight_digit_date_outside_19xx_20xx_is_still_masked_before_a_back(text, date):
    # 주민번호 탐지기는 19·20으로 시작하는 8자리만 받는다. 생년월일 탐지기가 다른 연도까지 넘기면 둘 다
    # 버려서, main이 가리던 날짜가 통째로 샜다(#508 독립 검증)
    assert_masked(text, date)


def test_eight_digit_birthdate_alone_is_still_a_birthdate():
    # 뒷자리가 없으면 지금처럼 생년월일이다(#508 대조군)
    assert {d.kind for d in Pipeline().scan("생년월일 19800101")} == {"birth_date"}


def test_birthdate_label_with_two_parenthetical_notes():
    # 라벨 뒤 괄호 설명을 두 개까지 받는다(#508). 괄호 안 숫자 금지는 그대로다(위 괄호 회귀 테스트)
    assert "1999-07-21" in texts(BirthDateDetector(), "생년월일(만 나이)(한국식) 1999-07-21")


@pytest.mark.parametrize(
    "text",
    [
        "생년월일 (만 나이) 1999-07-21",  # 라벨과 괄호 사이에 공백(#529)
        "생년월일 (만 나이) (한국식) 1999-07-21",  # 괄호마다 앞에 공백
        "생년월일(만)(양력)(한국식) 1999-07-21",  # 붙여 쓴 괄호 세 개(#508은 두 개까지만 받았다)
    ],
)
def test_birthdate_label_with_spaced_or_triple_parenthetical_notes(text):
    # #508은 라벨에 바로 붙은 괄호 두 개까지만 받았다 — 라벨과 괄호 사이 공백이나 괄호
    # 세 개는 놓쳐서 날짜가 원문 그대로 샜다(#529).
    assert "1999-07-21" in texts(BirthDateDetector(), text)


# ── 전화 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, value",
    [
        ("TEL 02)555-1234", "02)555-1234"),
        ("대표 031)123-4567", "031)123-4567"),
        ("전화 +82-2-555-1234", "+82-2-555-1234"),
        ("전화 +82 31 123 4567", "+82 31 123 4567"),
        ("휴대폰 +82 (0)10-1234-5678", "+82 (0)10-1234-5678"),
        ("연락처 (+82) 10-1234-5678", "(+82) 10-1234-5678"),
        ("연락처 +820212345678", "+820212345678"),
    ],
)
def test_phone_forms(text, value):
    assert value in texts(PhoneDetector(), text)
    assert_masked(text, value)


@pytest.mark.parametrize(
    "text, value",
    [
        # 새 표기가 앞에서 먼저 시작해 뒤 번호를 반쯤 삼키던 회귀(#493 독립 검증) — 뒤 번호 전체가 가려진다
        ("02) 031-1234-5678", "031-1234-5678"),
        ("+82-2-031-1234-5678", "031-1234-5678"),
        ("+82 (0)10 010-1234-5678", "010-1234-5678"),
        ("지역번호 02) 070-1234-5678", "070-1234-5678"),
    ],
)
def test_new_phone_forms_do_not_swallow_the_next_number(text, value):
    assert_masked(text, value)


def test_year_in_parentheses_is_still_not_a_phone():
    assert PhoneDetector().detect("(2024) 1234-5678") == []


# ── 계좌 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, value",
    [
        ("입금계좌-110-123-456789", "110-123-456789"),
        ("신한은행 110-123-456789-홍길동", "110-123-456789"),
        ("입금 계좌 110-123-456789- 확인", "110-123-456789"),
    ],
)
def test_account_with_attached_hyphen(text, value):
    assert value in texts(AccountDetector(), text)
    assert_masked(text, value)


def test_account_inside_a_longer_hyphenated_number_is_still_skipped():
    # 숫자-숫자로 이어진 더 긴 번호의 일부는 계좌가 아니다
    assert AccountDetector().detect("입금 계좌 참조번호 12-110-123-456789-34") == []


@pytest.mark.parametrize(
    "text",
    [
        "입금 확인 주문번호 ORD-2000-0816-7063",
        "입금 요청 INV-2012-0918-337991-KR",
        "입금 요청 2012-0918-337991-KR",  # 뒤에만 영문 코드
    ],
)
def test_account_inside_a_latin_code_is_skipped(text):
    # 영문 코드에 하이픈으로 붙은 숫자는 주문번호·송장번호의 일부다(#493 독립 검증)
    assert AccountDetector().detect(text) == []


# ── 카드 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    [
        "6212 3456 7890 1234 569",  # 19자리 4-4-4-4-3 (Luhn 통과)
        "3056 930902 5904",  # 14자리 4-6-4 (Luhn 통과)
        "4111-1111 1111-1111",  # 구분자가 섞인 16자리
    ],
)
def test_card_forms(value):
    assert value in texts(CreditCardDetector(), "카드 " + value)


def test_sixteen_digit_card_followed_by_more_digits_is_still_found():
    # 19자리 모양이 "16자리 카드 + 뒤 숫자 3개"를 삼킨 뒤 체크섬에서 버려져도 16자리 카드는 잡는다
    assert "4111 1111 1111 1111" in texts(CreditCardDetector(), "카드 4111 1111 1111 1111 123원")


def test_card_matching_several_shapes_is_reported_once():
    assert texts(CreditCardDetector(), "카드 4111-1111-1111-1111") == ["4111-1111-1111-1111"]


@pytest.mark.parametrize(
    "text",
    [
        "학년도 2023-2024 2025-2026",
        "품번 1111-2222 3333-4444",
        "체크리스트 2025-2021 2020-2030 항목",  # 문맥어가 낱말 일부로만 맞는 경우(#493 독립 검증)
    ],
)
def test_mixed_separator_numbers_without_a_card_cue_are_not_cards(text):
    assert CreditCardDetector().detect(text) == []


def test_card_forms_still_need_luhn():
    assert CreditCardDetector().detect("카드 6212 3456 7890 1234 560") == []


# ── 여권 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, value",
    [
        ("여권번호 M 12345678", "M 12345678"),
        ("여권번호: M-12345678", "M-12345678"),
        ("여권 m 123A4567", "m 123A4567"),
    ],
)
def test_passport_with_a_separator_near_the_word_passport(text, value):
    assert value in texts(PassportDetector(), text)


def test_passport_with_a_separator_needs_the_word_passport():
    # "여권" 없이 문자와 숫자 사이가 떨어진 코드는 여권번호로 보지 않는다(오탐 방지)
    assert PassportDetector().detect("사이즈 S 12345678 재고") == []
    assert PassportDetector().detect("문서번호 D-20260928") == []
