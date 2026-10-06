# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""판결문의 판사·검사·증인, 소속 뒤 자기소개, 띄어 쓴 받는 사람 옆 이름이 새던 문제(#663).

판결문은 이름이 개인정보가 되는 대표 문서인데 판사·검사·증인 자리를 규칙도 로컬 LLM도 놓쳤다.
"검사"는 일반어와 겹치므로 이름 앞에서, 이름 뒤가 낱말 경계일 때만 받는다. 오탐 방지 문장은
main에서 모두 빈 결과였고 그대로여야 한다.
"""

import pytest

from maskingtape.detectors import NameDetector


def _names(text: str) -> list[str]:
    return [text[d.start : d.end] for d in NameDetector().detect(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("판사 정재아", ["정재아"]),
        ("검사 황수재(기소, 공판)", ["황수재"]),
        ("검사 황수재는 공소를 제기하였다", ["황수재"]),
        ("증인 문양석의 증언에 의하면", ["문양석"]),
        ("정재아 판사", ["정재아"]),
        ("문양석 증인은", ["문양석"]),
        ("고객센터 송준경입니다.", ["송준경"]),
        ("영업팀 황수재입니다.", ["황수재"]),
        ("제 이름은 황은민이고요,", ["황은민"]),
        ("받는 사람: 송준경 <minsu.kim@example.com>", ["송준경"]),
    ],
)
def test_names_now_found(text: str, expected: list[str]) -> None:
    assert _names(text) == expected


def test_existing_control_still_found() -> None:
    assert _names("변호인 변호사 문양석") == ["문양석"]


@pytest.mark.parametrize(
    "text",
    [
        "검사 결과를 알려드립니다",
        "검사 장비를 점검했다",
        "검사 진단서를 첨부합니다",
        "검사 성적서 발급",
        "유전자 검사를 받았다",
        "정확도 검사 결과",
        "안전성 검사 통과",
        "보안 검사 결과입니다",
        "라이선스 검사 통과",
        "판사 출신 변호사",
        "판사 임명장을 받았다",
        "증인 진술서 제출",
        "증인 신문 조서",
        "고객센터 안내문입니다",
        "운영팀 정산서입니다",
        "영업팀 회의입니다",
        "회의 결과 정리본입니다",
        "개발팀 공지입니다",
        "인사팀 신청서입니다",
        "고객센터 전화번호입니다",
        "영업팀 김과장입니다",
        "담당자 정리하고요",
    ],
)
def test_common_words_are_not_names(text: str) -> None:
    assert _names(text) == []
