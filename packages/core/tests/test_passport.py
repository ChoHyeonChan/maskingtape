# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""여권번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다.

여권번호는 검증 체크섬이 없어 형식만 맞춘 가짜다(실제 발급번호와 무관).
"""

from maskingtape.detectors import PassportDetector


def detect(text: str):
    return PassportDetector().detect(text)


def test_detects_old_format_with_context():
    found = detect("여권번호 M12345678 확인 바랍니다")
    assert len(found) == 1
    assert found[0].kind == "passport"
    assert found[0].text == "M12345678"
    assert found[0].confidence == 0.9  # 문맥어 '여권'이 근처에 있어 확신도 상향


def test_detects_new_generation_format():
    # 차세대 전자여권: 문자 + 3자리 + 문자 + 4자리
    found = detect("여권 M123A4567 재발급 신청")
    assert len(found) == 1
    assert found[0].text == "M123A4567"


def test_format_only_gets_lower_confidence():
    # 문맥어 없이 형식만이면 낮은 확신도(과탐=안전, 임계값으로 조절 가능)
    found = detect("참조코드 M12345678 입니다")
    assert len(found) == 1
    assert found[0].confidence == 0.6


def test_detects_all_valid_passport_prefixes():
    for letter in "MSROD":
        found = detect(f"여권번호 {letter}12345678")
        assert len(found) == 1, f"{letter} prefix 미탐지"


def test_rejects_invalid_letter_prefix():
    # M/S/R/O/D 외의 문자로 시작하면 여권번호 표기가 아니다
    assert detect("여권 A12345678") == []
    assert detect("여권 Z12345678") == []


def test_rejects_wrong_length():
    assert detect("여권 M1234567") == []      # 8자리 미만
    assert detect("여권 M123456789") == []    # 8자리 초과


def test_does_not_grab_from_longer_alphanumeric():
    # 앞뒤에 영숫자가 더 붙으면 더 긴 코드의 일부다 — 오려내지 않는다
    assert detect("XM12345678") == []
    assert detect("M12345678X") == []


# --- 소문자 표기 (#398) ---
# 여권번호는 대문자로 발급되지만 문서에 옮겨 적을 때 소문자가 섞인다.
# 대소문자 하나로 통째로 놓치면 그대로 유출이므로 구분하지 않는다.


def test_detects_lowercase_old_format():
    found = detect("여권번호 m12345678 확인 바랍니다")
    assert len(found) == 1
    assert found[0].text == "m12345678"
    assert found[0].confidence == 0.9


def test_detects_lowercase_new_generation_format():
    found = detect("여권 m123a4567 재발급 신청")
    assert len(found) == 1
    assert found[0].text == "m123a4567"


def test_detects_mixed_case_new_generation_format():
    # 사람이 옮겨 적으면 대소문자가 섞인다
    found = detect("여권번호 M123a4567")
    assert len(found) == 1
    assert found[0].text == "M123a4567"


def test_lowercase_without_context_keeps_lower_confidence():
    # 대문자와 같은 규칙 — 문맥어가 없으면 0.6
    found = detect("참조코드 m12345678 입니다")
    assert len(found) == 1
    assert found[0].confidence == 0.6


def test_detects_all_valid_prefixes_in_lowercase():
    for letter in "msrod":
        found = detect(f"여권번호 {letter}12345678")
        assert len(found) == 1, f"소문자 {letter} prefix 미탐지"


def test_still_rejects_invalid_lowercase_prefix():
    # 소문자를 허용해도 여권 종류 코드가 아닌 문자는 잡지 않는다
    for letter in "abcqz":
        assert detect(f"여권번호 {letter}12345678") == [], f"{letter}는 여권 접두가 아니다"
