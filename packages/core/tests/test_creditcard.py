"""신용카드번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다.

여기 쓰는 번호는 업계 표준 '테스트 카드번호'(4242…, 4111… 등)로 실제 발급되지 않는다.
Luhn 체크섬만 만족하는 가짜다.
"""

from maskingtape.detectors.creditcard import CreditCardDetector


def detect(text: str):
    return CreditCardDetector().detect(text)


def test_detects_card_with_hyphens():
    found = detect("결제 카드 4242-4242-4242-4242 승인")
    assert len(found) == 1
    assert found[0].kind == "card"
    assert found[0].text == "4242-4242-4242-4242"
    assert found[0].confidence == 0.95


def test_detects_card_with_spaces():
    found = detect("카드번호 4111 1111 1111 1111")
    assert len(found) == 1
    assert found[0].text == "4111 1111 1111 1111"


def test_detects_bare_16_digits():
    found = detect("5555555555554444")
    assert len(found) == 1


def test_detects_15_digit_amex():
    found = detect("아멕스 3782 822463 10005")
    assert len(found) == 1


def test_detects_dot_separated_card():
    # 보안 리뷰에서 발견: 점 구분자 카드가 누락되면 금융정보가 그대로 유출된다
    found = detect("결제 4111.1111.1111.1111 완료")
    assert len(found) == 1
    assert found[0].text == "4111.1111.1111.1111"


def test_detects_card_with_spaced_hyphen_separator():
    found = detect("카드 4111 - 1111 - 1111 - 1111")
    assert len(found) == 1


def test_does_not_join_numbers_across_a_newline():
    # 서로 다른 줄의 무관한 숫자를 하나의 카드로 잇지 않는다 (오탐 방지)
    found = detect("주문 4111\n1111222233334444 접수")
    assert all("\n" not in d.text for d in found)


def test_rejects_number_failing_luhn():
    # 자릿수는 맞지만 Luhn을 통과 못 하는 숫자열은 카드번호가 아니다
    assert detect("4242-4242-4242-4243") == []
    assert detect("1234 5678 1234 5678") == []


def test_rejects_too_short_or_too_long():
    # 전화번호(11자리)나 지나치게 긴 숫자열은 카드가 아니다
    assert detect("010-1234-5678") == []
    assert detect("12345678901234567890123") == []


def test_does_not_grab_digits_from_a_longer_run():
    # 앞뒤에 숫자가 더 붙은 긴 숫자열의 일부를 카드로 오려내지 않는다
    assert detect("9994242424242424242999") == []
