# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 앞뒤 단서 단어 테스트 — 모든 이름은 합성(가짜)이다."""

import pytest

from maskingtape.detectors import NameDetector


def detect(text: str):
    return NameDetector().detect(text)


# ── 역할어 "상담원"(#580) ───────────────────────────────────────────
# "상담사"는 직함 단서였지만 같은 뜻의 "상담원"은 없어서, 고객센터 상담 기록처럼 존칭 없이
# "담당 상담원 김민수"로 쓰면 이름을 통째로 놓쳤다.


@pytest.mark.parametrize(
    "text, name",
    [
        ("담당 상담원 김민수", "김민수"),
        ("상담원 박서준에게 감사 인사를 남김", "박서준"),
        ("[상담 1] 전화 상담 · 담당 상담원 강태오", "강태오"),
        ("김민수 상담원이 안내했습니다", "김민수"),
    ],
)
def test_counselor_role_word_is_a_name_cue(text, name):
    assert name in [d.text for d in detect(text)]


@pytest.mark.parametrize(
    "text", ["상담원 연결 대기 중입니다", "상담원 연결해 드릴게요", "상담원 배정은 내일"]
)
def test_counselor_followed_by_a_common_word_is_not_a_name(text):
    # "상담사"와 같은 직함 규칙을 따른다 — 직함만 단서일 땐 성+2자 풀네임만 받고, 흔한 낱말은 거른다.
    assert detect(text) == []
