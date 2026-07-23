"""이메일 탐지기 테스트 — 모든 주소는 합성(가짜)이다."""

import time

from maskingtape.detectors.email import EmailDetector


def test_detects_email_in_korean_sentence():
    found = EmailDetector().detect("문의는 hong.gildong+test@example.co.kr 로 주세요")
    assert len(found) == 1
    assert found[0].kind == "email"
    assert found[0].text == "hong.gildong+test@example.co.kr"


def test_rejects_handle_without_domain():
    # 도메인이 없는 @핸들은 이메일이 아니다
    assert EmailDetector().detect("트위터 @maskingtape 계정") == []


def test_detects_email_at_rfc_length_limits():
    # RFC 5321 상한(로컬 64자)까지는 정상 탐지돼야 한다 — 상한을 너무 좁히면 놓친다
    local = "a" * 64
    text = f"연락처 {local}@example.com 입니다"
    found = EmailDetector().detect(text)
    assert len(found) == 1
    assert found[0].text == f"{local}@example.com"


def test_long_text_without_at_sign_stays_fast():
    """ReDoS 회귀 방지: '@'가 없는 긴 문자열에서 시간이 폭발하면 안 된다.

    반복에 상한이 없던 시절 40만 자 처리에 1.4초가 걸렸다(입력 길이의 제곱으로 증가).
    MCP 파일 도구는 10MB까지 허용하므로 서비스 거부로 이어질 수 있었다.
    """
    text = "0" * 400_000
    start = time.perf_counter()
    assert EmailDetector().detect(text) == []
    elapsed = time.perf_counter() - start
    # 수정 후 수 ms 수준. CI 성능 편차를 감안해 넉넉히 잡되, 제곱 증가는 반드시 걸리게 한다.
    assert elapsed < 1.0, f"이메일 탐지가 너무 느립니다({elapsed:.2f}s) — 정규식 상한이 빠졌는지 확인"
