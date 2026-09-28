# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""core detector들의 ReDoS(정규식 과다 역추적) 방지 회귀 테스트.

핵심 계약: 여러 detector의 docstring/주석에 "정규식 반복에 상한을 둬 ReDoS를 막는다"가
명시돼 있다(email.py가 실측 사례까지 남김 — 40만 자, `@` 없음 입력이 상한 없던 시절엔
1.4초였다). 하지만 이 속성을 지키는 자동 테스트가 없어서, 누군가 정규식을 느슨하게
고치면(#162) 이 회귀를 아무도 못 잡는다. 각 detector에 적대적 입력(구분자·특수문자 없이
쭉 이어진 긴 문자열)을 넣고 시간 예산 안에 끝나는지 확인해 이 속성을 고정한다.

아래 두 절: 위쪽(`_CASES`)은 손으로 고른 고정 입력 몇 개로 절대 시간(5초) 안에 끝나는지
보고, 아래쪽(#480)은 무작위로 조립한 입력으로 "길이를 2배로 늘리면 시간이 몇 배로 느는지"
비율을 본다. 손으로 고른 입력만으로는 우리가 예상 못 한 글자 조합에서만 역추적이 폭발하는
정규식 회귀를 놓칠 수 있어서 보강한다(팀장 결정 #480 — hypothesis 대신 표준 라이브러리
random으로 직접 짜서 새 의존성·SBOM 절차가 필요 없다).
"""

from __future__ import annotations

import random
import time

import pytest
from maskingtape.detectors import (
    AccountDetector,
    AddressDetector,
    BirthDateDetector,
    BusinessRegistrationDetector,
    CreditCardDetector,
    EmailDetector,
    NameDetector,
    PassportDetector,
    PhoneDetector,
    RRNDetector,
)
from maskingtape.detectors.financial.account import (
    _BANK_NAMES_ADJACENT,
    _BANK_NAMES_ADJACENT_LATIN,
    _BANK_NAMES_LOCAL,
    _BANK_NAMES_LONG,
    _BANK_NAMES_NEARBY,
)
from maskingtape.detectors.personal.address import _JOSA, _PROVINCE_ABBR, _PROVINCES

# 상한 없는 정규식이 겪는 catastrophic backtracking은 입력 길이의 제곱 이상으로 느려지므로,
# 정상적인 상한 있는 정규식이라면 40만 자도 수 초 안에 끝나야 한다. 여유 있게 5초로 잡는다
# (CI 환경 속도 편차 감안 — 목적은 "역추적 폭발이 없다"지 정밀 벤치마크가 아니다).
_TIME_BUDGET_SECONDS = 5.0
_LENGTH = 400_000


def _repeat_to_length(unit: str, length: int = _LENGTH) -> str:
    """unit을 이어 붙여 정확히 length자로 맞춘다 — 매칭이 수만 건 나는 입력을 만들 때 쓴다."""
    return (unit * (length // len(unit) + 1))[:length]


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
    # birthdate는 앵커(생일/생년월일)+공백열이 폭발 입력이다 — 다른 탐지기의 "0"*N 입력으론
    # 트리거되지 않아 이 케이스가 빠져 있었고, 그래서 #289 ReDoS를 회귀 테스트가 못 잡았다.
    ("birth_date", BirthDateDetector(), "생일" + " " * _LENGTH),
    # 위 address 입력("가"*N)은 시/도명 같은 앵커가 하나도 없어 매칭이 0건이다. #426은 정규식이
    # 아니라 **매칭 뒤의 파이썬 반복문**(겹침 검사)이 O(n²)이던 문제라, 매칭이 수만 건 나는
    # 입력이어야만 드러난다(수정 전 80~90초, 수정 후 0.34초 이내). 앵커 종류별로 겹침 검사
    # 경로가 달라 세 가지를 모두 넣는다 — core의 시간 회귀 테스트가 쓴 입력과 같은 구성이다.
    ("address_repeat_abbr_road", AddressDetector(), _repeat_to_length("서울 강남구 대동로 ")),  # 축약형 앵커끼리
    ("address_repeat_province_si", AddressDetector(), _repeat_to_length("서울특별시 강남구 역삼동에서 ")),  # 시/도 구간 × 시 앵커
    ("address_repeat_abbr_jibun", AddressDetector(), _repeat_to_length("경기 성남시 분당구 정자동 45-6 ")),  # 축약형 구간 × 시 앵커
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


# --- #480: 무작위(property-based 스타일) 퍼징으로 고정 케이스가 놓치는 조합을 넓힌다 ---
#
# 위 _CASES처럼 절대 시간(5초)을 무작위 입력에 걸면 CI 서버 속도 편차로 흔들린다. 대신
# "입력 길이를 2배로 늘리면 시간이 몇 배로 느는지" 비율을 본다 — 선형이면 대략 2배,
# 제곱이면 4배, 역추적 폭발이면 훨씬 커진다. 시드를 고정해(_FUZZ_SEED) n자·2n자 입력이
# 항상 같은 접두사를 갖게 만든다(rng가 매번 같은 순서로 조각을 고르므로) — 그래야 "모양은
# 같고 길이만 다른" 비교가 되고, CI에서 실패해도 같은 입력을 그대로 재현할 수 있다.
#
# detect()를 한 번씩만 재면 OS가 다른 프로세스에 CPU를 뺏는 순간과 겹쳐 흔들리기 쉬워서,
# 같은 텍스트로 여러 번 반복해 process_time(프로세스가 실제로 쓴 CPU 시간, 다른 프로세스에
# 뺏긴 시간은 안 잡힘) 누적값을 비교한다.
_FUZZ_SEED = 480
_FUZZ_BASE_LENGTH = 50_000
_FUZZ_MAX_RATIO = 3.0

# 탐지기 어휘로 입력을 조립해야 역추적 경로를 탄다 — 아무 글자나 섞으면 정규식이 금방
# 포기한다. core의 목록 상수를 그대로 import해서 core가 목록을 바꿔도 따라간다.
_ADDRESS_FUZZ_PIECES = (
    list(_PROVINCES) + list(_PROVINCE_ABBR) + _JOSA.split("|") + ["시", "군", "구", "동", "읍", "면", "리", " "]
)
_ACCOUNT_FUZZ_PIECES = (
    list(_BANK_NAMES_NEARBY)
    + list(_BANK_NAMES_LOCAL)
    + list(_BANK_NAMES_LONG)
    + list(_BANK_NAMES_ADJACENT)
    + list(_BANK_NAMES_ADJACENT_LATIN)
    + [str(d) for d in range(10)]
    + ["-", " ", "계좌", "입금"]
)

_RATIO_CASES = [
    ("address_fuzz", AddressDetector(), _ADDRESS_FUZZ_PIECES, 10),
    ("account_fuzz", AccountDetector(), _ACCOUNT_FUZZ_PIECES, 30),
]


def _fuzz_string(pieces: list[str], target_len: int) -> str:
    """항상 같은 시드로 시작해 조각을 이어 붙인다.

    target_len이 다른 두 호출도 짧은 쪽 길이까지는 내용이 완전히 같다 — 매번 새
    `random.Random(_FUZZ_SEED)`로 시작해 같은 순서로 조각을 고르기 때문이다.
    """
    rng = random.Random(_FUZZ_SEED)
    parts: list[str] = []
    total = 0
    while total < target_len:
        piece = rng.choice(pieces)
        parts.append(piece)
        total += len(piece)
    return "".join(parts)[:target_len]


def _total_process_time(detector, text: str, iterations: int) -> float:
    start = time.process_time()
    for _ in range(iterations):
        detector.detect(text)
    return time.process_time() - start


@pytest.mark.parametrize("kind,detector,pieces,iterations", _RATIO_CASES, ids=[c[0] for c in _RATIO_CASES])
def test_detector_time_scales_linearly_when_input_doubles(kind, detector, pieces, iterations):
    text_n = _fuzz_string(pieces, _FUZZ_BASE_LENGTH)
    text_2n = _fuzz_string(pieces, _FUZZ_BASE_LENGTH * 2)

    time_n = _total_process_time(detector, text_n, iterations)
    time_2n = _total_process_time(detector, text_2n, iterations)

    ratio = time_2n / time_n
    assert ratio < _FUZZ_MAX_RATIO, (
        f"{kind}: 입력 길이를 2배({_FUZZ_BASE_LENGTH}자→{_FUZZ_BASE_LENGTH * 2}자)로 늘렸더니 "
        f"시간이 {ratio:.2f}배로 늘어남(선형이면 ~2배) — 정규식 역추적 회귀(ReDoS) 의심"
    )
