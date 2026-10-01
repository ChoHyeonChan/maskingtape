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


# ── 버린 후보가 뒤 직함을 삼키지 않는다(#580) ─────────────────────────
# "고객이 대리 김민수에게"에서 규칙은 먼저 "고객이"를 이름 후보, "대리"를 그 뒤 직함으로 읽는다.
# "고객이"는 일반어라 버리는데, 그때 "대리"까지 소비하고 지나가 "대리"가 김민수의 앞 단서가
# 되지 못했다 — 직함 앞 낱말이 성씨 글자로 시작하면 뒤 이름이 통째로 샜다(main에서 재현).


@pytest.mark.parametrize(
    "text, name",
    [
        ("고객이 대리 김민수에게 전달", "김민수"),
        ("고객이 팀장 박서준에게 보고", "박서준"),
        ("고객이 상담원 이하은에게 감사", "이하은"),
    ],
)
def test_rejected_candidate_does_not_swallow_the_next_title_cue(text, name):
    assert name in [d.text for d in detect(text)]
