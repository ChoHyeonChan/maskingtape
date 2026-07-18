"""이메일 탐지기 테스트 — 모든 주소는 합성(가짜)이다."""

from maskingtape.detectors.email import EmailDetector


def test_detects_email_in_korean_sentence():
    found = EmailDetector().detect("문의는 hong.gildong+test@example.co.kr 로 주세요")
    assert len(found) == 1
    assert found[0].kind == "email"
    assert found[0].text == "hong.gildong+test@example.co.kr"


def test_rejects_handle_without_domain():
    # 도메인이 없는 @핸들은 이메일이 아니다
    assert EmailDetector().detect("트위터 @maskingtape 계정") == []
