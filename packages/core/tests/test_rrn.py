# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""RRN 탐지기 테스트. 모든 번호는 합성(가짜)이다 — 진짜 개인정보 커밋 금지."""

import pytest

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


def test_gender_digit_alone_does_not_swallow_a_longer_number():
    # 성별 숫자 뒤에 진짜 숫자·영문이 더 붙으면(다른 번호의 일부일 수 있으므로) "성별 숫자만
    # 남은 표기"로 오인해 앞부분만 잘라 잡으면 안 된다 — 뒤에 뭐가 더 있으면 형태가 안 맞는
    # 것이므로 통째로 버린다(오탐 방지). 7자리(가짜 뒷자리 자리수)가 아니면 온전한 RRN도 아니다.
    assert RRNDetector().detect("생년월일 19800101-12") == []


def test_bare_gender_digit_without_any_separator_context_is_not_falsely_grabbed():
    # 구분자 없이 붙여 쓴 "800101" 뒤에 성별 숫자로 보일 법한 숫자 하나만 있고 더 이어지면
    # (예: 전화번호 뒷자리 일부) 오탐하지 않는다 — 뒤에 숫자가 더 있으므로 경계에서 걸러진다
    assert RRNDetector().detect("800101 1234") == []


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
