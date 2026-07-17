"""RRN 탐지기 테스트. 모든 번호는 합성(가짜)이다 — 진짜 개인정보 커밋 금지."""

from maskingtape.detectors.rrn import RRNDetector

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


def test_rejects_impossible_birthdate():
    # 13월 32일은 날짜가 아니므로 탐지하면 안 된다
    assert RRNDetector().detect("991332-1234567") == []


def test_rejects_longer_digit_runs():
    # 앞뒤로 숫자가 더 붙은 긴 수열(계좌번호 등)은 주민번호가 아니다
    assert RRNDetector().detect("98001011234560123") == []
