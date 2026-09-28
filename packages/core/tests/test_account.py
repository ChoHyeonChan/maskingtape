# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""계좌번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다."""

import pytest

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer
from maskingtape.detectors import AccountDetector


def detect(text: str):
    return AccountDetector().detect(text)


def test_detects_account_after_bank_name():
    found = detect("급여는 국민은행 123-456789-01-011로 지급합니다")
    assert len(found) == 1
    assert found[0].kind == "account"
    assert found[0].text == "123-456789-01-011"
    assert found[0].confidence == 0.6


def test_detects_account_with_cue_word():
    found = detect("계좌 110-234-567890으로 입금 바랍니다")
    assert [f.text for f in found] == ["110-234-567890"]


def test_detects_kakao_style_seven_digit_group():
    # 카카오뱅크식 3333-01-1234567 (마지막 그룹 7자리)
    found = detect("예금주 홍길동, 이체 계좌 3333-01-1234567")
    assert [f.text for f in found] == ["3333-01-1234567"]


def test_detects_plain_digits_near_cue():
    found = detect("급여 이체 계좌 110234567890 입니다")
    assert [f.text for f in found] == ["110234567890"]


def test_ignores_number_without_context_cue():
    # 은행명·계좌 관련어가 없으면 그냥 숫자열이므로 버린다 (오탐 방지)
    assert detect("주문번호 2301011234561 확인 바랍니다") == []
    assert detect("상품코드 123-456789-01-011") == []


def test_ignores_phone_like_number_without_account_cue():
    # 전화번호 문맥에서는 계좌로 오탐하지 않는다
    assert detect("전화 문의 010-1234-5678") == []


def test_ignores_out_of_range_digit_count():
    # 계좌 문맥이어도 자릿수가 범위(10~14) 밖이면 버린다
    assert detect("계좌 12-345") == []  # 5자리
    assert detect("계좌 1234-5678-9012-3456-7890") == []  # 20자리


# --- #472: 은행 이름만 붙은 번호, 마지막 묶음이 한 자리인 번호 ---


@pytest.mark.parametrize(
    ("text", "number"),
    [
        ("신한 110-123-456789", "110-123-456789"),
        ("농협 302-1234-5678-91 홍길동", "302-1234-5678-91"),
        ("NH농협 302-1234-5678-91", "302-1234-5678-91"),
        ("카뱅 3333-01-1234567", "3333-01-1234567"),
        ("SC제일 123-45-678901", "123-45-678901"),
        ("수협 1010-1234-5678", "1010-1234-5678"),
        ("신협 홍길동 131-012-345678", "131-012-345678"),  # 이름이 사이에 있어도 창 안이다
        ("신협중앙회 131-012-345678", "131-012-345678"),  # 신협약·신협정만 거르고 신협은 받는다
        ("110-123-456789 신한 홍길동", "110-123-456789"),  # 번호 뒤에 와도 창 안이다
        # 지역 이름을 앞에 붙인 상호금융 — 이름 뒤가 낱말 끝이면 받는다
        ("안성농협 351-1234-5678-91", "351-1234-5678-91"),
        ("관악신협 131-012-345678", "131-012-345678"),
        ("제주수협 1010-1234-5678", "1010-1234-5678"),
        ("안성축협 351-1234-5678-91", "351-1234-5678-91"),
        # 긴 이름은 앞뒤 글자와 상관없이 받는다
        ("화곡새마을금고 9002-1234-5678-1", "9002-1234-5678-1"),
        ("화곡새마을금고에서 9002-1234-5678-1로", "9002-1234-5678-1"),
        ("양평산림조합 1234-56-123456", "1234-56-123456"),
    ],
)
def test_bank_name_near_number_is_a_cue(text, number):
    """다른 낱말과 헷갈리지 않는 은행 이름은 창(±15자) 안에만 있으면 문맥어다."""
    assert [f.text for f in detect(text)] == [number]


def test_bank_name_window_is_fifteen_characters():
    """은행 이름은 번호 앞뒤 15자 안에 있어야 한다. 16자 떨어지면 문맥이 아니다."""
    number = "110-123-456789"
    assert [f.text for f in detect("신한" + " " * 13 + number)] == [number]
    assert detect("신한" + " " * 14 + number) == []
    assert [f.text for f in detect(number + " " * 13 + "신한")] == [number]
    assert detect(number + " " * 14 + "신한") == []


@pytest.mark.parametrize(
    ("text", "number"),
    [
        ("우리 1002-123-456789", "1002-123-456789"),
        ("회비는 우리 1002-123-456789로 보내주세요", "1002-123-456789"),
        ("하나 123-456789-01234", "123-456789-01234"),
        ("국민 123456-01-123456", "123456-01-123456"),
        ("KB국민 123456-01-123456", "123456-01-123456"),
        ("KB 123456-01-123456", "123456-01-123456"),
        ("IBK기업 010-123456-01-011", "010-123456-01-011"),
        ("우체국 012345-01-012345", "012345-01-012345"),
        ("토스 1000-1234-5678", "1000-1234-5678"),
        ("카카오 3333-01-1234567", "3333-01-1234567"),
        ("부산 101-2034-5678-09", "101-2034-5678-09"),
        ("우리: 1002-123-456789", "1002-123-456789"),
        ("(우리) 1002-123-456789", "1002-123-456789"),
        ("우리1002-123-456789", "1002-123-456789"),
        ("1002-123-456789 (우리)", "1002-123-456789"),
        ("1002-123-456789(하나)", "1002-123-456789"),
        ("우리\u00a01002-123-456789", "1002-123-456789"),  # 줄바꿈 없는 공백(NBSP)
        ("우리/1002-123-456789/홍길동", "1002-123-456789"),
        ("국민 - 123456-01-123456", "123456-01-123456"),
        ("우리 :  1002-123-456789", "1002-123-456789"),  # 사이 글자 4자
    ],
)
def test_everyday_word_bank_name_right_before_number_is_a_cue(text, number):
    """일상어와 겹치는 은행 이름은 번호 바로 앞이나, 번호 뒤 괄호 안일 때만 문맥어다."""
    assert [f.text for f in detect(text)] == [number]


@pytest.mark.parametrize(
    "text",
    [
        # 일상어가 번호와 떨어져 있다 — 계좌가 아닌 번호다
        "우리 가게 주문번호 2026-0925-1234 확인 부탁드려요",
        "하나 더 보냈어요 송장번호 6123-4567-8901",
        "국민 여러분 민원번호 1234-5678-9012 로 조회하세요",
        "우체국 택배 운송장 6012-3456-7890",
        "토스 결제 주문번호 2026-0925-1234",
        "주문번호 2026-0925-1234 하나 더 주세요",  # 번호 뒤라도 괄호가 아니면 인정하지 않는다
        "1002-123-456789 우리 가게",
        "하나\n6123-4567-8901",  # 줄이 바뀌면 바로 앞이 아니다
        # 은행 이름이 다른 낱말의 일부다
        "혁신협의회 회의번호 2026-0925-1234",
        "특수협약 문서번호 2026-0925-1234",
        "영농협동 사업번호 2026-0925-1234",
        "한미 신협정 문서번호 2026-0925-1234",  # 신(新)+협정
        "신협약 체결 번호 2026-0925-1234",
        "신한류 공연 예매번호 2026-0925-1234",
        "신한일 어업협정 문서번호 1998-1128-0001",  # 신(新)+한일
        "갱신한 계약번호 2026-0925-1234",
        "건축협회 회원번호 2026-0925-1234",  # 앞뒤가 다 한글이면 낱말 한가운데다
        # 창 오른쪽 끝에 걸린 이름도 뒤 글자를 보고 거른다
        "번호 2026-0925-1234" + " " * 13 + "신한국 행사",
        "번호 2026-0925-1234" + " " * 13 + "신협약",
        "번호 2026-0925-1234" + " " * 12 + "신협의체",
        "결제일 2026-0925-1234",
        "용량 512KB 2026-0925-1234",
        "하나하나 2026-0925-1234 확인",  # 번호 바로 앞 "하나"가 "하나하나"의 일부다
    ],
)
def test_bank_name_that_is_not_a_cue(text):
    assert detect(text) == []


@pytest.mark.parametrize(
    ("text", "number"),
    [
        ("새마을금고 계좌 9002-1234-5678-1", "9002-1234-5678-1"),  # 새마을금고 4-4-4-1
        ("새마을금고 9002-1234-5678-1", "9002-1234-5678-1"),
        ("신협 계좌 12345-67-12345-1", "12345-67-12345-1"),  # 옛 신협 5-2-5-1
        ("계좌 1234-56-123456-7", "1234-56-123456-7"),  # 옛 새마을금고 4-2-6-1
    ],
)
def test_detects_one_digit_last_group(text, number):
    """마지막 묶음이 한 자리(검증 숫자)인 하이픈 표기도 잡는다."""
    assert [f.text for f in detect(text)] == [number]


@pytest.mark.parametrize(
    "text",
    [
        "계좌 1-2345-6789-012",  # 한 자리 묶음은 맨 끝에만 온다 (12자리)
        "계좌 1234-5-6789012",  # 가운데 한 자리 (12자리)
        "계좌 12-34-5",  # 5자리 — 자릿수 검증은 그대로다
        "계좌 12-34-56-7890-1",  # 묶음 5개 (11자리)
    ],
)
def test_one_digit_group_stays_narrow(text):
    assert detect(text) == []


def test_bank_name_cue_does_not_relabel_phone_numbers():
    """지역 이름 은행(부산 등) 바로 뒤의 전화번호는 계좌가 아니라 전화번호로 남는다.

    겹치면 확신도가 높은 쪽 종류를 따르는데, 전화번호(0.95~1.0)가 계좌(0.6)보다 높다.
    """
    result = Pipeline().scan("부산 051-123-4567, 하나 010-1234-5678")
    assert [(d.kind, d.text) for d in result] == [
        ("phone", "051-123-4567"),
        ("phone", "010-1234-5678"),
    ]


def test_bank_name_only_account_is_masked_end_to_end():
    result = Pipeline(anonymizer=LabelAnonymizer()).anonymize(
        "회비는 신한 110-123-456789, 새마을금고 9002-1234-5678-1로 보내주세요"
    )
    assert "110-123-456789" not in result.text
    assert "9002-1234-5678-1" not in result.text
    assert [d.kind for d in result.detections] == ["account", "account"]


# --- #474: 하이픈 대신 공백·점으로 나눈 계좌번호 ---


@pytest.mark.parametrize(
    ("text", "number"),
    [
        ("입금 계좌 1002 123 456789", "1002 123 456789"),
        ("계좌 110 123 456789 홍길동", "110 123 456789"),
        ("신한 110 123 456789", "110 123 456789"),
        ("신한 110.123.456789", "110.123.456789"),
        ("우리 1002 123 456789", "1002 123 456789"),  # 일상어 은행 이름이 바로 앞
        ("새마을금고 계좌 9002 1234 5678 1", "9002 1234 5678 1"),  # 끝 묶음 한 자리
        ("계좌: 356.12.098765 (국민은행)", "356.12.098765"),
    ],
)
def test_detects_space_or_dot_separated_account(text, number):
    assert [f.text for f in detect(text)] == [number]


@pytest.mark.parametrize(
    ("text", "number"),
    [
        # 뒤에 띄어 쓴 숫자가 이어져도 계좌번호 전체가 가려진다. 조건에 맞는 창을 전부 모아 합치므로
        # 뒤 숫자까지 함께 가릴 수 있다(더 가리는 쪽이라 안전). 이렇게 해야 농협 3-4-4-2·새마을금고
        # 4-4-4-1처럼 끝 묶음이 짧은 번호도 끝까지 잡는다.
        ("입금 계좌 1002 123 456789 2026 09 25 확인", "1002 123 456789"),
        ("계좌 110 123 456789 12 34", "110 123 456789"),
        ("농협 302 1234 5678 91", "302 1234 5678 91"),
    ],
)
def test_space_separated_account_followed_by_other_numbers(text, number):
    """계좌번호 전체가 한 탐지 안에 들어간다(뒤 숫자를 더 가리는 건 허용)."""
    start = text.index(number)
    end = start + len(number)
    found = detect(text)
    assert len(found) == 1
    assert found[0].start <= start and found[0].end >= end


@pytest.mark.parametrize(
    "text", ["계좌 110-123-456789 12 34", "계좌 110-123-456789 2026 09 25 입금"]
)
def test_hyphenated_account_is_not_swallowed_by_trailing_spaced_digits(text):
    """하이픈 번호는 예전 그대로 잡는다. 뒤에 띄어 쓴 숫자와 한 덩어리로 묶이지 않는다."""
    assert [f.text for f in detect(text)] == ["110-123-456789"]


@pytest.mark.parametrize(
    "text",
    [
        "주문번호 1002 123 456789 확인",  # 계좌 문맥이 없다
        "입금일 2026 09 28",  # 8자리
        "계좌 개설일 2026.09.28",  # 날짜
        "입금 앱 버전 3.12.1",
        "계좌 110 123-456789",  # 한 번호 안에서 구분자가 섞이면 받지 않는다
        "입금 1 234 567 890",  # 첫 묶음이 한 자리
        "계좌 1002\n123\n456789",  # 줄바꿈은 구분자가 아니다
    ],
)
def test_space_or_dot_separated_non_accounts(text):
    assert detect(text) == []


def test_spaced_phone_and_card_keep_their_own_kind():
    """공백 구분 전화·카드번호 옆에 계좌 문맥어가 있어도 종류는 전화·카드로 남고 끝까지 가려진다.

    계좌 후보가 겹쳐도 파이프라인은 합집합으로 가리고, 종류는 확신도가 높은 쪽(전화 1.0,
    카드 0.95 > 계좌 0.6)을 따른다.
    """
    text = "입금 문의 010 1234 5678, 입금 대신 카드 4111 1111 1111 1111 결제"
    result = Pipeline(anonymizer=LabelAnonymizer()).anonymize(text)
    assert [d.kind for d in result.detections] == ["phone", "card"]
    assert "010 1234 5678" not in result.text
    assert "4111 1111 1111 1111" not in result.text


_TAB, _NBSP, _IDEOGRAPHIC_SPACE = chr(9), chr(0xA0), chr(0x3000)


@pytest.mark.parametrize(
    ("text", "number"),
    [
        # 구분자 변형 — 공백 두 칸, 탭, NBSP, 전각 공백, 띄운 하이픈, 점+공백
        ("입금 계좌 110  123  456789", "110  123  456789"),
        (f"입금 계좌 110{_TAB}123{_TAB}456789", f"110{_TAB}123{_TAB}456789"),
        (f"입금 계좌 110{_NBSP}123{_NBSP}456789", f"110{_NBSP}123{_NBSP}456789"),
        (
            f"입금 계좌 110{_IDEOGRAPHIC_SPACE}123{_IDEOGRAPHIC_SPACE}456789",
            f"110{_IDEOGRAPHIC_SPACE}123{_IDEOGRAPHIC_SPACE}456789",
        ),
        ("입금 계좌 110 - 123 - 456789", "110 - 123 - 456789"),
        ("입금 계좌 110. 123. 456789", "110. 123. 456789"),
        ("카뱅 3333 01 1234567", "3333 01 1234567"),  # 7자리 묶음
        ("계좌번호-1002 123 456789", "1002 123 456789"),  # 글자 뒤 하이픈은 숫자를 잇지 않는다
        ("입금일 2026.09.28 1002 123 456789", "1002 123 456789"),  # 점 날짜와 공백 계좌는 섞지 않는다
    ],
)
def test_detects_separator_variants(text, number):
    assert [f.text for f in detect(text)] == [number]


@pytest.mark.parametrize(
    ("text", "number"),
    [
        # 앞에 띄어 쓴 숫자가 있어도 계좌 뒷부분이 남지 않는다 (창을 전부 모아 합친다)
        ("입금 계좌 020 1002 123 456789", "1002 123 456789"),
        ("입금 09.28 30000 1002 123 456789 홍길동", "1002 123 456789"),
        ("입금 2026 09 28 1002 123 456789", "1002 123 456789"),
        # 묶음이 많아도(상한 없음) 계좌를 끊어 먹지 않는다
        ("입금 1 2 3 4 5 6 1002 123 456789", "1002 123 456789"),
        ("입금 내역 3 2026 09 28 14 30 50000 1002 123 456789", "1002 123 456789"),
    ],
)
def test_account_after_other_spaced_numbers_is_fully_masked(text, number):
    start = text.index(number)
    end = start + len(number)
    assert any(f.start <= start and f.end >= end for f in detect(text))


@pytest.mark.parametrize(
    "text",
    [
        "입금 일시 2026 09 28 14 30",  # 날짜로 시작하는 창은 계좌가 아니다
        "입금 2026.09.28.1234 처리",
        "은행 내부망 192.168.100.200 접속",  # IPv4 모양
        "입금액 12,345,678,900원",  # 쉼표는 금액의 천 단위라 구분자가 아니다
    ],
)
def test_dates_ips_and_money_near_cues_are_not_accounts(text):
    assert detect(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "입금 금액 150000. 2026 09 28 처리",  # 문장 끝 점이 두 숫자를 잇지 않는다
        "입금 확인 1234567.890 원",  # 2묶음 점은 소수점이다
    ],
)
def test_two_group_dot_is_not_an_account(text):
    assert detect(text) == []


@pytest.mark.parametrize(
    ("text", "kinds"),
    [
        ("입금자 주민번호 800101 1234560. 010 1234 5678 연락", ["rrn", "phone"]),
        ("입금 카드 4111 1111 1111 1111 - 800101 1234560", ["card", "rrn"]),
    ],
)
def test_sentence_dot_or_spaced_hyphen_does_not_bridge_two_numbers(text, kinds):
    """문장 끝 점이나 띄운 하이픈 하나로 이어진 두 번호를 계좌 후보가 잇지 않는다(종류가 유지된다)."""
    assert [d.kind for d in Pipeline().scan(text)] == kinds


@pytest.mark.parametrize(
    ("text", "number"),
    [("통장 110-123-456789", "110-123-456789"), ("통장 사본 1002 123 456789", "1002 123 456789")],
)
def test_bankbook_is_a_cue(text, number):
    assert [f.text for f in detect(text)] == [number]


def test_spaced_number_next_to_hyphenated_number_keeps_both_kinds():
    """공백 전화번호 바로 뒤에 하이픈 사업자번호가 와도 둘을 한 계좌 후보로 잇지 않는다.

    이으면 파이프라인이 한 구간으로 합쳐 전화 종류가 보고에서 빠진다.
    """
    result = Pipeline().scan("입금 문의 02 3456 7890 123-45-67891")
    assert [d.kind for d in result] == ["phone", "biz_reg"]


def test_space_separated_account_masked_end_to_end():
    result = Pipeline(anonymizer=LabelAnonymizer()).anonymize("입금 계좌 1002 123 456789 (우리은행)")
    assert result.text == "입금 계좌 [계좌번호] (우리은행)"
