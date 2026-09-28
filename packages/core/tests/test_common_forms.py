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


# ── 전화 ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, value",
    [
        ("TEL 02)555-1234", "02)555-1234"),
        ("대표 031)123-4567", "031)123-4567"),
        ("전화 +82-2-555-1234", "+82-2-555-1234"),
        ("전화 +82 31 123 4567", "+82 31 123 4567"),
        ("휴대폰 +82 (0)10-1234-5678", "+82 (0)10-1234-5678"),
    ],
)
def test_phone_forms(text, value):
    assert value in texts(PhoneDetector(), text)


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
