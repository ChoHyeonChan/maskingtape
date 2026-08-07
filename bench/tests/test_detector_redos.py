"""core detector들의 ReDoS(정규식 과다 역추적) 방지 회귀 테스트.

핵심 계약: 여러 detector의 docstring/주석에 "정규식 반복에 상한을 둬 ReDoS를 막는다"가
명시돼 있다(email.py가 실측 사례까지 남김 — 40만 자, `@` 없음 입력이 상한 없던 시절엔
1.4초였다). 하지만 이 속성을 지키는 자동 테스트가 없어서, 누군가 정규식을 느슨하게
고치면(#162) 이 회귀를 아무도 못 잡는다. 각 detector에 적대적 입력(구분자·특수문자 없이
쭉 이어진 긴 문자열)을 넣고 시간 예산 안에 끝나는지 확인해 이 속성을 고정한다.
"""

from __future__ import annotations

import time

import pytest

from maskingtape.detectors import (
    AccountDetector,
    AddressDetector,
    BusinessRegistrationDetector,
    CreditCardDetector,
    EmailDetector,
    NameDetector,
    PassportDetector,
    PhoneDetector,
    RRNDetector,
)

# 상한 없는 정규식이 겪는 catastrophic backtracking은 입력 길이의 제곱 이상으로 느려지므로,
# 정상적인 상한 있는 정규식이라면 40만 자도 수 초 안에 끝나야 한다. 여유 있게 5초로 잡는다
# (CI 환경 속도 편차 감안 — 목적은 "역추적 폭발이 없다"지 정밀 벤치마크가 아니다).
_TIME_BUDGET_SECONDS = 5.0
_LENGTH = 400_000

_CASES = [
    ("email", EmailDetector(), "0" * _LENGTH),  # email.py docstring의 실측 시나리오와 동일
    ("phone", PhoneDetector(), "0" * _LENGTH),
    ("rrn", RRNDetector(), "1" * _LENGTH),
    ("card", CreditCardDetector(), "1" * _LENGTH),
    ("biz_reg", BusinessRegistrationDetector(), "1" * _LENGTH),
    ("passport", PassportDetector(), "M" * _LENGTH),
    ("address", AddressDetector(), "가" * _LENGTH),
    ("name", NameDetector(), "김" * _LENGTH),
    ("account", AccountDetector(), "1" * _LENGTH),
]


@pytest.mark.parametrize("kind,detector,text", _CASES, ids=[c[0] for c in _CASES])
def test_detector_handles_adversarial_input_within_time_budget(kind, detector, text):
    start = time.perf_counter()
    detector.detect(text)
    elapsed = time.perf_counter() - start
    assert elapsed < _TIME_BUDGET_SECONDS, (
        f"{kind} detector가 적대적 입력({len(text)}자)에서 {elapsed:.2f}초 걸림 "
        f"(예산 {_TIME_BUDGET_SECONDS}초) — 정규식 역추적 회귀(ReDoS) 의심"
    )
