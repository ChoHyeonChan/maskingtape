# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""신용카드번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다.

여기 쓰는 번호는 업계 표준 '테스트 카드번호'(4242…, 4111… 등)로 실제 발급되지 않는다.
Luhn 체크섬만 만족하는 가짜다.
"""

from maskingtape.detectors import CreditCardDetector


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
    """구분자가 없으면 묶음 정보가 없으므로 Luhn만으로 판정한다.

    카드번호를 붙여 쓴 경우를 놓치면 금융정보 유출이므로, 여기서는 넉넉한 쪽을 택한다.
    """
    found = detect("4715343756648")
    assert len(found) == 1


def test_detects_card_when_preceded_by_unrelated_digits():
    """카드 앞에 공백으로 분리된 무관한 숫자가 있어도 카드를 놓치지 않는다.

    예전엔 정규식이 앞 숫자와 카드를 하나로 삼킨 뒤 검증 실패로 버려, 진짜 카드가
    마스킹되지 않고 유출됐다(금융정보 유출).
    """
    assert detect("번호 123456 4242-4242-4242-4242")[0].text == "4242-4242-4242-4242"
    assert detect("수량 12 4242 4242 4242 4242")[0].text == "4242 4242 4242 4242"
    assert detect("1 4242424242424242")[0].text == "4242424242424242"


def test_card_must_start_with_a_four_digit_group():
    """구분자가 있으면 4자리 그룹으로 시작해야 한다 — 3-4-4(전화)나 6-7(주민번호)은 카드가 아니다."""
    assert detect("010-1234-5678") == []
    assert detect("123-4567-8901-2345") == []  # 3자리 시작


# ─── #510: 카드 두 장이 이어질 때 뒤 카드가 새지 않는다 ───────────────────────────


def _covered(text: str, card: str, start_at: int = 0) -> bool:
    """text 안 start_at 이후 처음 나오는 card의 모든 글자가 어떤 탐지 구간 안에 들어가는지."""
    begin = text.index(card, start_at)
    spans = [(d.start, d.end) for d in detect(text)]
    return all(any(s <= i < e for s, e in spans) for i in range(begin, begin + len(card)))


def test_second_card_after_mixed_separator_card_is_fully_detected():
    """이슈 원문 — 앞 카드의 뒤 두 묶음과 뒤 카드의 앞 두 묶음을 이은 숫자열이 Luhn을 우연히
    통과해 먼저 잡히고, finditer가 그 끝부터 다시 찾아 진짜 뒤 카드를 검사하지 않았다.
    뒤 카드의 마지막 묶음 "1111"이 원문으로 남았다."""
    text = "카드 4111-1111 1111-1111 4111 1111 1111 1111"
    assert _covered(text, "4111-1111 1111-1111")
    assert _covered(text, "4111 1111 1111 1111")


def test_mixed_separator_card_right_after_another_card_is_detected():
    """뒤 카드가 하이픈·공백을 섞어 쓰면 섞인 모양 정규식으로만 잡히는데, 연도 목록 오탐을 막는
    카드 문맥어("카드")가 앞 15자 밖이라 버려져 **뒤 카드가 통째로** 남았다."""
    mixed_then_mixed = "카드 4111-1111 1111-1111 4111-1111 1111-1111"
    assert _covered(mixed_then_mixed, "4111-1111 1111-1111")
    assert _covered(mixed_then_mixed, "4111-1111 1111-1111", start_at=10)

    space_then_mixed = "카드 4111 1111 1111 1111 4111-1111 1111-1111"
    assert _covered(space_then_mixed, "4111 1111 1111 1111")
    assert _covered(space_then_mixed, "4111-1111 1111-1111")

    comma_between = "카드 4111-1111 1111-1111, 4242-4242 4242-4242"
    assert _covered(comma_between, "4242-4242 4242-4242")


def test_adjacent_cards_leave_no_digits_after_masking():
    """파이프라인 끝까지 — 이어진 카드 두 장의 숫자가 마스킹 결과에 하나도 남지 않는다."""
    from maskingtape.pipeline import Pipeline

    pipeline = Pipeline()
    for text in (
        "카드 4111-1111 1111-1111 4111 1111 1111 1111",
        "카드 4111-1111 1111-1111 4111-1111 1111-1111",
        "카드 4111 1111 1111 1111 4111-1111 1111-1111",
    ):
        masked = pipeline.anonymize(text).text
        assert not any(ch.isdigit() for ch in masked), f"{text!r} → {masked!r}"


def test_mixed_separator_year_list_without_card_cue_is_still_ignored():
    """섞인 모양을 카드 뒤에 이어 받게 한 뒤에도, 카드 문맥이 없는 연도 목록은 그대로 무시한다."""
    assert detect("재직 기간 2023-2024 2025-2026") == []
    assert detect("사업 기간 2015-2016 2017-2018, 2019-2020 2021-2022") == []


def test_year_list_right_after_a_card_is_not_taken_as_a_second_card():
    """카드 뒤 이어받기가 연도 목록 오탐을 다시 열지 않는다 — 차등 검사에서 나온 경우다.
    "1999-2009 2014-2004"는 Luhn을 통과하지만, 네 묶음이 모두 연도라 카드로 받지 않는다."""
    text = "카드 4111-1111 1111-1111 1999-2009 2014-2004"
    years = text.index("1999")
    assert all(d.end <= years for d in detect(text))
    # 같은 모양이라도 앞에 카드 문맥어가 직접 있으면 예전처럼 문맥어 규칙을 따른다(변화 없음).
    assert detect("카드 1999-2009 2014-2004") != []



# ── 카드 종류 라벨이 바로 앞에 있으면 Luhn이 틀려도 낮은 확신도로 가린다(#607) ──────
# 손으로 옮겨 적다 한 자리 틀린 번호, OCR·음성 받아쓰기 결과는 라벨이 "이건 카드번호다"라고
# 말해 주는데 검증 숫자 하나 때문에 번호 전체가 남았다. 라벨 없는 형식만 맞는 숫자열은 그대로 버린다(#87).


def test_labeled_card_failing_luhn_is_still_masked_with_low_confidence():
    found = detect("카드번호 4111-1111-1111-1112")
    assert len(found) == 1
    assert found[0].text == "4111-1111-1111-1112"
    assert found[0].confidence == 0.6


def test_labeled_card_with_colon_failing_luhn_is_still_masked():
    found = detect("카드번호: 1234-5678-9012-3456")
    assert len(found) == 1
    assert found[0].text == "1234-5678-9012-3456"
    assert found[0].confidence == 0.6


def test_labeled_card_passing_luhn_keeps_full_confidence():
    # 대조군: 체크섬이 맞는 카드는 라벨 유무와 관계없이 확신도 0.95 그대로다
    found = detect("카드번호 4111-1111-1111-1111")
    assert len(found) == 1
    assert found[0].confidence == 0.95


def test_card_failing_luhn_without_a_card_label_is_still_dropped():
    # 라벨이 없으면 검증 숫자가 틀린 숫자열은 여전히 카드가 아니다(#87 오탐 가드 유지)
    assert detect("주문 4111-1111-1111-1112") == []
    assert detect("결제 4111-1111-1111-1112") == []
