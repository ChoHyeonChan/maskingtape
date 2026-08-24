# SPDX-License-Identifier: Apache-2.0

"""계좌번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다."""

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
