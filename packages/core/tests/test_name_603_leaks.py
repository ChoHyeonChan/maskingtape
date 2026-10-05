# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""#603(PR #647)에서 더한 단서·라벨이 기존 경로를 바꿔 새던 이름(#674). 모든 이름·번호는 합성이다.

#603 전에는 가리던 꼴이다. 새 단서는 새로 잡는 꼴에만 쓰고, 기존 경로는 전처럼 둔다.
"""

import pytest

from maskingtape.detectors import NameDetector


def covered(text: str, name: str, nth: int = 0) -> bool:
    start = -1
    for _ in range(nth + 1):
        start = text.index(name, start + 1)
    spans = [(d.start, d.end) for d in NameDetector().detect(text)]
    return any(s <= start and start + len(name) <= e for s, e in spans)


@pytest.mark.parametrize(
    "text, name",
    [
        # A. #603 직함이 앞 단서가 되어도 그 뒤 두 글자 이름은 다른 단서(괄호)로 전처럼 잡는다
        ("피고 김민(35세)은 혐의를 부인했다.", "김민"),
        ("원고 이준(42세)은 소를 제기했다.", "이준"),
        ("버스 기사 최한(52세)이 운전했다.", "최한"),
        ("요양원 입소 어르신 김순(82세)이 퇴소했다.", "김순"),
        ("담당 책임 김민(서명)", "김민"),
        # B. "원고"로 시작하는 이름을 직함+조사로 읽지 않는다
        ("담당자 원고은에게 서류를 전달했다.", "원고은"),
        ("고객 원고은", "원고은"),
        ("신청자: 원고은", "원고은"),
        # "원고은"을 "원고(앞 단서)+은(조사)"으로 읽지 않는다
        ("담당 원고은 차장", "원고은"),
        ("참석: 원고은 조교,", "원고은"),
        ("서류: 원고은 주임님께", "원고은"),
        # C. 경계 없는 뒤 직함(원고·박사)이 다음 이름의 앞머리를 먹지 않는다
        ("오늘 원고은 님이 방문했습니다.", "원고은"),
        ("김민수 원고은 씨", "원고은"),
        ("오늘자 원고은 부팀장님께", "원고은"),
        # D. 앞 단서가 있으면 두 글자 이름 + 배상도 전처럼 잡는다
        ("주식회사 마스킹 담당자 이준 배상", "이준"),
        ("고객 김민 배상.", "김민"),
    ],
)
def test_names_masked_before_603_are_still_masked(text, name):
    assert covered(text, name), NameDetector().detect(text)


@pytest.mark.parametrize(
    "text",
    [
        "번호,수신,성명,연락처\n1,인사팀,김민수,010-1234-5678\n2,총무팀,이서연,010-2345-6789",
        "| 순번 | 서명 | 성명 |\n| 1 | (인) | 김민수 |\n| 2 | (인) | 이서연 |",
        "| 작성 | 검토 | 승인 |\n| 번호 | 성명 | 연락처 |\n| 1 | 김민수 | 010-1234-5678 |\n| 2 | 이서연 | 010-2345-6789 |",
    ],
)
def test_short_603_labels_do_not_pick_the_table_name_column(text):
    # E. 수신·서명·작성 같은 짧은 라벨은 표의 이름 열 머리가 아니다. 진짜 성명 열을 가린다.
    assert covered(text, "김민수") and covered(text, "이서연"), NameDetector().detect(text)


@pytest.mark.parametrize(
    "text, name",
    [
        # F. #603 단서 낱말이 나열 중간에 와도 뒤 이름까지 이어받는다
        ("참석자: 김민수, 구매자, 이서연", "이서연"),
        ("참석자: 김민수, 주문자, 이서연", "이서연"),
        # 기존 앞 단서 바로 뒤 이름 자리에 #603 단서 낱말이 와도 그 뒤 나열은 이어받는다
        ("의뢰인 : 구매자,정민가,김혜실씨", "정민가"),
        ("이름,번호\n성명,예금주\n박사,최한", "최한"),
        ("작성,비고,성명\n신고인,장민지,김민", "장민지"),
        # G. #603 상태 값(본사·전체 등)이 양식 값이나 나열 칸에 와도 그 뒤 나열은 이어받는다
        ("수취인 | 본사씨,정민가!", "정민가"),
        ("계약자 : 권율 님과 전체님,조이씨 그리고 김민,", "김민"),
    ],
)
def test_603_cue_words_do_not_cut_a_list(text, name):
    assert covered(text, name), NameDetector().detect(text)


@pytest.mark.parametrize(
    "text, name, nth",
    [
        # 표에 이름 라벨 열이 여럿이면 다 가린다(전에는 첫 열만 가려 둘째 이름 열이 샜다)
        ("| 이름 | 성명 | 비고 |\n|---|---|---|\n| 김가을 | 홍길동 | 박지훈 |", "홍길동", 0),
        ("서명 / 예금주\n조이 / 정민\n홍길동 / 이준", "정민", 0),
        # #603으로 새로 잡던 꼴은 지킨다
        ("서명 / 예금주\n조이 / 정민\n홍길동 / 이준", "조이", 0),
        ("수신|번호\n임채원|홍길동", "임채원", 0),
        ("원고는 김민수에게 돈을 빌려주었다.", "김민수", 0),
        ("박사은 김민수", "김민수", 0),
        ("기사은 김민수", "김민수", 0),
        ("어제 선임은 : 홍길동", "홍길동", 0),
    ],
)
def test_table_name_columns_and_603_gains(text, name, nth):
    assert covered(text, name, nth), NameDetector().detect(text)


@pytest.mark.parametrize(
    "text, name",
    [
        # #603 앞 단서 + 일반어 + 뒤 단서 + 이름: 뒤 단서가 다음 이름의 앞 단서로 남는다
        ("구매자 문의 담당자 이서연", "이서연"),
        ("운전자 정보 작성자 박지훈", "박지훈"),
        ("피고인 조사 담당자 김도현 경위", "김도현"),
        ("박사 이하은\n환자명 김도현", "김도현"),
        # 양식·표 값이 #603 단서+조사 모양이어도 이름으로 받는다(성씨 사전 밖 이름)
        ("성명: 피고은", "피고은"),
        ("성명,연락처\n피고은,010-1234-5678", "피고은"),
        ("보호자: 배우자가, 김도현", "김도현"),
        # 나열 사이 "박사랑"은 실명이다
        ("참석자: 김도현 박사랑 이하늘", "박사랑"),
        # #603 라벨 낱말이 값 자리에 와도 그 뒤 나열은 이어받는다
        ("보호자: 결재, 김도현, 이하늘", "이하늘"),
    ],
)
def test_603_cues_do_not_take_over_old_paths(text, name):
    assert covered(text, name), NameDetector().detect(text)


@pytest.mark.parametrize(
    "text, name",
    [
        # #603 앞 단서로 실명을 받은 뒤 그 뒤 직함을 다음 이름의 앞 단서로 빼앗지 않는다
        ("구매자 김민수 대표 이준(인)", "이준"),
        ("피고인 김도현 대리 이준(42세)은 범행을 부인했다.", "이준"),
        ("피해자 박서윤 팀장\n최한(서명)", "최한"),
        ("주문자 김도현 과장\n문의 담당자 이서연", "이서연"),
        ("구매자: 김도현 대리\n배송 담당자: 이서연", "이서연"),
        ("피보험자 피고인 이은실 양이 전무열(남, 41세)", "전무열"),
        # 값 자리가 띄어 쓴 양식 라벨로 시작하면 그 라벨부터 다시 본다
        ("서명: 면허 갱신 신청: 김민수", "김민수"),
        ("서명(한글) : 면허 갱신 신청(한글)| 곽민재", "곽민재"),
    ],
)
def test_603_prefix_does_not_steal_the_next_cue(text, name):
    assert covered(text, name), NameDetector().detect(text)


@pytest.mark.parametrize(
    "text, name",
    [
        # #603 앞 단서 뒤 일반어를 건너뛰고 다시 찾은 직함이 두 글자 이름의 유일한 앞 단서여도, 괄호 같은
        # 다른 단서로 잡는다(#676)
        ("구매자 정보\n대표 이준(인)", "이준"),
        ("피고인 조사\n대표 이준(42세)", "이준"),
        ("구매자 정보 대표 이준(인) 담당자 김민수", "이준"),
        ("구매자 정보 대표 이준(인) 담당자 김민수", "김민수"),
    ],
)
def test_resumed_cue_keeps_two_char_name_with_other_cue(text, name):
    assert covered(text, name), NameDetector().detect(text)
