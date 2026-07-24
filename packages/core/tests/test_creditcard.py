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


def test_rejects_resident_registration_number_shape():
    """6-7로 끊어 쓴 13자리는 주민등록번호 표기지 카드가 아니다.

    아래 두 값은 bench distractor(존재하지 않는 월/일로 만든 '주민번호 모양' 합성값)로,
    13자리라 자릿수 범위에 들어오고 Luhn까지 우연히 통과해 카드로 오탐됐었다.
    """
    assert detect("송장번호 471534-3756648로 배송 시작") == []
    assert detect("결제일 191739-2343897, 금액 확인") == []


def test_rejects_id_number_shape_with_space_separator():
    # 구분자가 공백이어도 6-7 묶음이면 카드 표기가 아니다
    assert detect("471534 3756648") == []


def test_rejects_real_resident_registration_number_as_card():
    """유효한 주민등록번호도 카드로는 잡지 않는다 — RRNDetector가 담당한다.

    체크섬만 맞춘 합성 번호다.
    """
    assert detect("주민번호 800101-1234560 확인") == []


def test_bare_13_digits_still_judged_by_luhn_alone():
    """구분자가 없으면 묶음 정보가 없으므로 지금처럼 Luhn만으로 판정한다.

    카드번호를 붙여 쓴 경우를 놓치면 금융정보 유출이므로, 여기서는 넉넉한 쪽을 택한다.
    """
    found = detect("4715343756648")
    assert len(found) == 1
