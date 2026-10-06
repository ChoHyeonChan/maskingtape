# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""판결문의 판사·검사·증인, 띄어 쓴 받는 사람, 어미 "이고요" 옆 이름이 새던 문제(#663).

판결문은 이름이 개인정보가 되는 대표 문서인데 판사·검사·증인 자리를 규칙도 로컬 LLM도 놓쳤다.
세 단서는 일반어와 겹치므로 이름 앞에서만, 이름 뒤가 낱말 경계일 때만 받는다. 새 단서가 기존
단서 경로를 바꿔 전보다 덜 가리는 일이 없어야 한다(독립 검증에서 찾은 반례를 그대로 넣었다).
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
        ("받는 사람: 송준경 <minsu.kim@example.com>", ["송준경"]),
        ("제 이름은 황은민이고요,", ["황은민"]),
    ],
)
def test_names_now_found(text: str, expected: list[str]) -> None:
    assert _names(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # 기존 단서 경로가 그대로여야 한다(새 단서를 공용 거르기·두 글자 직함 규칙에 넣었다가 샌 꼴)
        ("변호인 변호사 문양석", ["문양석"]),
        ("배우자: 유효성", ["유효성"]),
        # 첫 칸은 성씨+직함 꼴(이상무)이 아닌 이름으로 둔다. 그 꼴은 #677 규칙이 성씨만 가린다
        ("피해자|이상민, 김민수, 박지훈", ["이상민", "김민수", "박지훈"]),
        ("유효성 선수가 골을 넣었다.", ["유효성"]),
        ("배우자: 신청서, 김민수, 박지훈", ["신청서", "김민수", "박지훈"]),
        ("피해자 이수가 증인으로 출석했다.", ["이수가"]),
        ("피고인 김하가 판사에게 반성문을 냈다.", ["김하가"]),
        ("피해자 이준의 증인 신문이 있었다.", ["이준의"]),
        # 새 단서 뒤의 "원고가"·"박사가"는 다음 이름의 앞 단서다
        ("검사 원고가 김민수를 고소했다.", ["김민수"]),
        ("검사 박사가 김민수를 만났다.", ["김민수"]),
        ("증인 원고가 김민수를 고소했다.", ["김민수"]),
        ("받는 사람 박사가 김민수에게", ["김민수"]),
    ],
)
def test_existing_paths_unchanged(text: str, expected: list[str]) -> None:
    assert _names(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "검사 결과를 알려드립니다",
        "검사 장비를 점검했다",
        "검사 진단서를 첨부합니다",
        "검사 성적서 발급",
        "검사 진행중.",
        "검사 방법은?",
        "유전자 검사를 받았다",
        "정확도 검사 결과",
        "안전성 검사 통과",
        "보안 검사 결과입니다",
        "라이선스 검사 통과",
        "판사 출신 변호사",
        "판사 임명장을 받았다",
        "판사 전원이 동의했다.",
        "판사 정원이 늘었다.",
        "증인 진술서 제출",
        "증인 신문 조서",
        "증인 신문이 열렸다.",
        "증인 신분으로 출석했다.",
        "담당자 정리하고요",
    ],
)
def test_common_words_are_not_names(text: str) -> None:
    assert _names(text) == []
