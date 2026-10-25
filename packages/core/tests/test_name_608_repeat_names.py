# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""한 번 잡은 이름이 같은 글 안에서 단서 없이 다시 나오는 자리(#608).

문서는 보통 첫 언급에만 역할어·존칭을 붙이고 그 뒤로는 이름만 쓴다. 첫 이름만 가리면 가린 자리가 누구인지
뒤에서 그대로 드러난다. 이미 이름으로 잡은 세 글자 이상 문자열이 같은 입력에 낱말 경계로 다시 나오면
그 자리도 가린다. 두 글자 이름은 일반 낱말과 겹쳐("이상"·"정원") 퍼뜨리지 않는다. 입력은 모두 합성이다.
"""

import pytest

from maskingtape.detectors import NameDetector


def _names(text: str) -> list[str]:
    return [text[d.start : d.end] for d in sorted(NameDetector().detect(text), key=lambda d: d.start)]


@pytest.mark.parametrize(
    ("text", "names"),
    [
        # 이슈 본문의 세 문장
        ("담당자 김민수입니다. 어제 김민수가 서류를 냈고, 김민수의 연락처는 따로 받았습니다.", ["김민수"] * 3),
        ("성명: 박서준\n박서준은 3월에 입사했다.", ["박서준"] * 2),
        ("고객 이서연님이 문의했습니다. 이서연은 환불을 원합니다.", ["이서연"] * 2),
        # 뒤에 오는 꼴: 조사 둘, 어미 첫머리, 문장부호, 줄 끝
        ("고객 이서연님이 문의했습니다. 이서연에게는 따로 연락했다.", ["이서연"] * 2),
        ("고객 이서연님이 문의했습니다. 이서연께서 다시 전화했다.", ["이서연"] * 2),
        ("고객 이서연님이 문의했습니다.\n처리: 이서연, 완료", ["이서연"] * 2),
        ("고객 이서연님이 문의했습니다. 다음 담당은 이서연.", ["이서연"] * 2),
        # 복성 네 글자
        ("담당자 남궁민수 대리가 왔다. 남궁민수는 서류를 두고 갔다.", ["남궁민수"] * 2),
        # 이름 여럿
        (
            "고객 이서연님과 담당자 김민수 대리가 만났다. 이서연은 김민수에게 환불을 요청했다.",
            ["이서연", "김민수", "이서연", "김민수"],
        ),
        # 다른 훑기(#663 자기소개)로 잡은 이름도 퍼뜨린다
        ("안녕하세요. 인사팀 김민수입니다. 김민수는 다음 주부터 휴가입니다.", ["김민수"] * 2),
        # 이름 전용 양식 라벨 뒤 이름
        ("예금주: 김민수\n김민수의 계좌로 보냈다.", ["김민수"] * 2),
        # 복성 + 한 글자 뒤에 한 글자가 더 붙으면 네 글자 이름일 수 있어 그 글자까지 가린다(하이브리드에서 끝 글자가 남지 않게)
        ("담당자 선우하입니다. 어제 선우하은이 서류를 냈다. 선우하은은 내일 온다.", ["선우하", "선우하은", "선우하은"]),
        ("제 이름은 남궁미입니다. 언니 남궁미란이 먼저 왔고, 남궁미란에게 서류를 줬다.", ["남궁미", "남궁미란", "남궁미란"]),
        # 뒤 글자가 앞 글자 받침과 맞지 않는 조사이거나 "라"면 더 긴 이름의 끝 글자일 수 있어 그 글자까지 가린다
        ("성명: 김하나\n김하나은이 서류를 냈다.", ["김하나", "김하나은"]),
        ("성명: 김하나\n김하나라는 내일 출근한다.", ["김하나", "김하나라"]),
        # 받침에 맞는 조사는 이름에 넣지 않는다
        ("성명: 김하나\n김하나는 내일 출근한다.", ["김하나"] * 2),
        ("성명: 박서준\n박서준이 서류를 냈다.", ["박서준"] * 2),
    ],
)
def test_repeated_name_is_masked_again(text: str, names: list[str]) -> None:
    assert _names(text) == names


@pytest.mark.parametrize(
    ("text", "names"),
    [
        # 더 긴 낱말의 앞부분이면 받지 않는다("이서연구소"·"김민수진")
        ("고객 이서연님이 문의했습니다. 이서연구소 자료입니다.", ["이서연"]),
        ("담당자 김민수입니다. 김민수진 씨는 다른 사람입니다.", ["김민수"]),
        # 앞이 한글이면 받지 않는다
        ("고객 이서연님이 문의했습니다. 박이서연은 다른 사람이다.", ["이서연"]),
        # 두 글자 이름은 퍼뜨리지 않는다
        ("고객 서윤님이 문의했습니다. 서윤은 환불을 원합니다.", ["서윤"]),
    ],
)
def test_repeat_needs_word_boundary_and_three_letters(text: str, names: list[str]) -> None:
    assert _names(text) == names


@pytest.mark.parametrize(
    "text",
    [
        # 단서 하나(0.5)로 잡힌 일반어 오탐은 문서 전체로 퍼뜨리지 않는다(첫 자리는 main 그대로)
        "대표 이미지는 첨부했다. 이미지는 PNG로 넣고, 이미지의 크기는 1MB 이하다.",
        "팀원 노트북으로 시연한다. 노트북은 미리 충전한다.",
        # 부서·업무 값이 흔한 라벨과 범용 라벨 "이름" 뒤 값은 확신도가 높아도 퍼뜨리지 않는다
        "수신: 정보통신\n정보통신에서 확인했다.",
        "작성: 품질관리\n품질관리는 다음 주에 한다.",
        "파일 이름: 보고서\n보고서는 내일 낸다.",
        # 직함 뒤 "입니다"는 원본이 아니다(교차검토)
        "대표 이미지입니다. 이미지는 PNG로 넣고 이미지를 첨부합니다.",
    ],
)
def test_single_cue_seed_does_not_spread(text: str) -> None:
    assert len(_names(text)) == 1


@pytest.mark.parametrize(
    "text",
    [
        # 표 칸·겹친 라벨에서 잡힌 부서 이름도 원본이 아니다(교차검토)
        "수신,부서\n정보통신,관리팀\n\n정보통신은 내일 회의합니다.",
        "성명: 수신: 정보통신\n정보통신은 확인했다.",
    ],
)
def test_table_and_nested_weak_label_values_do_not_spread(text: str) -> None:
    last = text.rindex("정보통신")
    assert all(not (d.start <= last < d.end) for d in NameDetector().detect(text))


def test_repeat_is_low_confidence_mode_only() -> None:
    """퍼뜨린 자리는 확신도 0.5다. 0.75 모드에서는 원래 탐지만 남는다."""
    text = "고객 이서연님이 문의했습니다. 이서연은 환불을 원합니다."
    found = NameDetector(min_confidence=0.75).detect(text)
    assert [text[d.start : d.end] for d in found] == ["이서연"]
    repeats = [d for d in NameDetector().detect(text) if d.start > 10]
    assert [d.confidence for d in repeats] == [0.5]
