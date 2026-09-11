# SPDX-License-Identifier: Apache-2.0

"""이메일 탐지기 테스트 — 모든 주소는 합성(가짜)이다."""

import time

from maskingtape.detectors import EmailDetector


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


# --- 한글 로컬 파트 (#400) ---
# RFC 6531(SMTPUTF8)이 국제화 주소를 규정하고 국내 일부 서비스가 실제로 발급한다.
# 한국어 특화 도구가 한글 이메일을 놓치면 그대로 유출이다.


def test_detects_hangul_local_part():
    found = EmailDetector().detect("문의: 홍길동@example.com 으로 보내주세요")
    assert len(found) == 1
    assert found[0].text == "홍길동@example.com"
    assert found[0].kind == "email"


def test_detects_hangul_local_part_mixed_with_ascii():
    # 실제 발급 주소는 한글과 영숫자가 섞이기도 한다
    found = EmailDetector().detect("담당자 김철수2@sample.org 연락")
    assert len(found) == 1
    assert found[0].text == "김철수2@sample.org"


def test_ascii_local_part_still_works():
    # 한글을 더해도 기존 영문 주소는 그대로 잡혀야 한다
    found = EmailDetector().detect("연락처 hong@example.com 입니다")
    assert len(found) == 1
    assert found[0].text == "hong@example.com"


def test_does_not_treat_korean_at_expressions_as_email():
    """도메인부를 영문 규칙으로 묶어 둔 덕분에 평범한 한국어 표현은 잡히지 않는다.

    로컬 파트만 넓히고 도메인은 `영문라벨.영문TLD`를 요구하는 것이 오탐을 막는 핵심이다.
    한글 도메인까지 허용하면 아래가 전부 이메일이 된다.
    """
    for text in ["회의@3층 회의실", "가격@10000원", "행사@서울시청", "문의@대표번호", "메일@없음"]:
        assert EmailDetector().detect(text) == [], f"{text!r}는 이메일이 아니다"


def test_does_not_treat_social_handle_as_email():
    # @가 앞에 붙는 멘션 표기는 로컬 파트가 없어 매치되지 않는다
    assert EmailDetector().detect("트위터 @홍길동 님께 문의") == []


def test_hangul_local_part_absorbs_preceding_characters_when_not_spaced():
    """알려진 한계 — 조사가 붙어 이어지면 앞 글자까지 로컬 파트로 잡는다.

    한국어는 띄어쓰기 없이 조사를 이어 붙일 수 있어서, 형태만으로는 `담당자는`이
    조사인지 주소의 일부인지 구분할 수 없다. 정규식은 각 위치에서 매치를 시도하므로
    lookbehind로도 막지 못한다.

    결과는 **과다 마스킹**이라 개인정보가 새지는 않는다. 현재 동작을 여기 고정해 두고,
    나중에 형태소 단위 경계 판단이 생기면 이 테스트가 실패하며 알려준다.
    """
    found = EmailDetector().detect("담당자는홍길동@example.com")
    assert len(found) == 1
    assert found[0].text == "담당자는홍길동@example.com"  # 과다 탐지(안전한 쪽)


def test_hangul_email_after_space_has_exact_span():
    # 앞에 공백이나 문장부호가 있으면 정확한 범위로 잡힌다 (실제 문서의 대부분)
    for text in ["보낸사람: 홍길동@example.com", "홍길동@example.com 님", "(홍길동@example.com)"]:
        found = EmailDetector().detect(text)
        assert len(found) == 1, f"{text!r} 미탐지"
        assert found[0].text == "홍길동@example.com", f"{text!r} 범위 오류: {found[0].text}"
