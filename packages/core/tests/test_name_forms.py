# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""양식 라벨 뒤 이름 표기(#491) 테스트 — 모든 이름은 합성(가짜)이다."""

import pytest

from maskingtape import Pipeline
from maskingtape.detectors import NameDetector


def names(text: str) -> list[str]:
    return [d.text for d in NameDetector().detect(text)]


# ── 라벨 뒤 구분자 ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, name",
    [
        ("성명 : 홍길동", "홍길동"),  # 양식에서 흔한 " : "(세 글자)
        ("이름 : 김민지", "김민지"),
        ("예금주 :  박서연", "박서연"),
        ("성명" + chr(9) + ":" + chr(9) + "홍길동", "홍길동"),  # 탭
        ("| 성명 | 홍길동 |", "홍길동"),  # 표 칸
        ("|성명|홍길동|", "홍길동"),
        ("성명(한글): 홍길동", "홍길동"),  # 괄호 설명
        ("신청인(대표자) : 이도현", "이도현"),
    ],
)
def test_form_separators_after_a_label(text, name):
    assert name in names(text)


@pytest.mark.parametrize(
    "text, name",
    [
        # 이름 전용 양식 라벨이 아닌 역할어 — 넓힌 구분자는 사전 성씨 규칙에서도 쓰인다
        ("담당자 : 홍길동", "홍길동"),
        ("| 고객 | 김민지 |", "김민지"),
        ("고객::김철수", "김철수"),  # 예전 규칙이 받던 "::"도 그대로
        ("성명::홍길동", "홍길동"),
        ("담당자   이도현 과장", "이도현"),  # 공백 세 칸
    ],
)
def test_widened_separator_for_other_role_words(text, name):
    assert name in names(text)


# ── 사전 밖 성씨: 이름 전용 라벨 + 쌍점·세로줄 ──────────────────────


@pytest.mark.parametrize(
    "text, name",
    [
        ("성명: 류서윤", "류서윤"),
        ("성명: 변서윤", "변서윤"),
        ("성명 : 탁서윤", "탁서윤"),
        ("| 이름 | 표하준 |", "표하준"),
        ("예금주: 탁서윤입니다", "탁서윤"),
        ("성함: 마동하님", "마동하"),
        ("성명: 연서", "연서"),  # 두 글자
    ],
)
def test_surname_outside_the_dictionary_after_a_form_label(text, name):
    assert name in names(text)


def test_name_ending_like_a_particle_is_not_cut_short():
    # "은"은 조사이기도 하지만 이름 끝 글자로 흔하다 — 떼어내면 그 글자가 샌다
    assert "류하은" in names("성명: 류하은")


@pytest.mark.parametrize(
    "text",
    [
        "성명: 없음",
        "성명: 미기재",
        "예금주: 본인",
        "이름: 해당없음",
        "성명: 미상",
        "예금주: 본인의 계좌",  # 뒤에 조사가 붙어도
        "예금주: 없음입니다",
        "| 성명 | 상동 |",
        "| 이름 | 설명 |",  # 표 머리행
        "| 성명 | 소속 | 직위 |",
        "성명(한글): 필수",
    ],
)
def test_placeholder_values_are_not_names(text):
    assert names(text) == []


@pytest.mark.parametrize(
    "text",
    [
        # 사전 밖 성씨(표·변·마·탁)로 시작하는 일반 낱말이 라벨 뒤에 오는 문장. 쌍점·세로줄이
        # 없으면 새 규칙을 쓰지 않는다 — 공백만으로 받으면 #484 같은 오탐이 는다.
        "이름 표기 규칙은 README에 있다.",
        "성명 변경 신청서를 냈다.",
        "예금주 마감 시각을 확인한다.",
        "성함 탁송 서비스 안내",
    ],
)
def test_new_rule_needs_a_colon_or_bar(text):
    assert names(text) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        # 괄호 안의 이름 — 예전 규칙이 잡던 것을 계속 잡는다(#491 독립 검증에서 찾은 회귀)
        ("담당자(김민수 대리) 이메일 kim@example.com", ["김민수"]),
        ("담당자(홍길동 과장) 전화 010-1234-5678", ["홍길동"]),
        ("고객(홍길동님) 김철수님", ["홍길동", "김철수"]),
        ("신청인(대리인 김철수) 성명: 이영희", ["김철수", "이영희"]),
        ("학생(박지훈 군) 성적 안내", ["박지훈"]),
    ],
)
def test_names_inside_parentheses_after_a_label(text, expected):
    found = names(text)
    assert all(name in found for name in expected)


@pytest.mark.parametrize(
    "text, name",
    [
        # 직함+조사("원장이")를 앞 단서 뒤의 이름으로 소비하면 그 직함이 뒤 이름의 단서가 되지 못한다
        # (#491 독립 검증 2회차). main이 가리던 뒤 이름을 계속 가린다.
        ("고객 : 원장이 김민수", "김민수"),
        ("담당자 : 차장은 김민수, 연락처 010-1234-5678", "김민수"),
        ("| 담당자 | 주임이 박서준 |", "박서준"),
        ("환자   원장이 김민수에게 인계", "김민수"),
        ("신청자 : 원장은 최하준입니다", "최하준"),
        ("고객: 원장이 김민수", "김민수"),  # 예전 구분자에서도 새던 모양
    ],
)
def test_title_with_particle_does_not_eat_the_next_name(text, name):
    masked = Pipeline().anonymize(text).text
    assert name not in masked, masked


@pytest.mark.parametrize(
    "text, name, title",
    [
        ("신청자 : 차장은 이도현입니다", "이도현", "차장은"),
        ("담당자 원장이 김민수에게 연락", "김민수", "원장이"),
        ("고객 : 원장이 김민수", "김민수", "원장이"),
        ("| 담당자 | 주임이 박서준 |", "박서준", "주임이"),
        ("신청자 : 원장은 최하준입니다", "최하준", "원장은"),
    ],
)
def test_title_with_particle_is_not_reported_as_a_name(text, name, title):
    # 직함+조사는 뒤 이름의 단서로만 쓰고 이름으로 보고하지 않는다(#533). 뒤 이름은 계속 가린다
    found = [d.text for d in Pipeline().scan(text) if d.kind == "name"]
    assert title not in found, found
    assert name in found, found
    assert title in Pipeline().anonymize(text).text


def test_label_glued_to_another_word_is_not_a_form_label():
    assert names("파일이름: 보고서") == []
    assert names("프로젝트이름: 테이프") == []


def test_label_on_the_next_line_is_not_taken_as_a_name():
    # 빈 칸 다음 줄의 라벨을 값으로 먹으면 진짜 이름이 샌다
    found = names("성명:" + chr(10) + "예금주: 류서윤")
    assert "류서윤" in found and "예금주" not in found


def test_label_in_the_value_position_is_skipped_and_searched_again():
    found = names("성명: 예금주: 류서윤")
    assert "류서윤" in found and "예금주" not in found


@pytest.mark.parametrize("name", ["기재민", "미정훈", "상동민", "동일환", "기재은", "기재이"])
def test_real_names_starting_like_a_placeholder_are_kept(name):
    # 자리표시 값은 완전히 같을 때만 거른다 — 앞부분만 같은 실명은 이름이다
    assert name in names("성명: " + name)


@pytest.mark.parametrize(
    "text, name",
    [
        # 사전 성씨 규칙은 일반명사(이하·이상)로 보고 버리거나 조사 모양 끝 글자를 뗀다 — 양식 칸 값은 살린다
        ("성명: 이하은", "이하은"),
        ("성명: 이상은", "이상은"),
        ("성명: 김가을", "김가을"),
    ],
)
def test_form_value_rescues_names_the_rule_path_drops(text, name):
    assert name in names(text)


def test_long_roster_stays_linear():
    import time

    def seconds(n: int) -> float:
        text = "성명: 김철수, 예금주: 류서윤. " * n
        start = time.perf_counter()
        NameDetector().detect(text)
        return time.perf_counter() - start

    seconds(200)
    small, large = seconds(1000), seconds(4000)
    assert large < 8 * small + 0.05  # 선형이면 약 4배, 제곱이면 약 16배


def test_dictionary_surnames_keep_their_old_behavior():
    assert names("신청자: 박서연 / 연락처: 010-1234-5678") == ["박서연"]
    assert names("고객 김철수님 010-1234-5678로 연락주세요") == ["김철수"]


# ── 업무 문서 제목형 라벨(#537) ────────────────────────────────────
# bench 실측(synth_v1)에서 규칙판이 놓친 50건 중 20건이 "라벨: 이름, 뒤정보"
# 형태였다 — "콤마 뒤 경계 판정 실패"가 원인일 거라는 추정과 달리, 실제로는
# "이력서 접수"·"면허 갱신 신청"이라는 라벨 문구 자체가 어휘(_FORM_LABELS)에
# 없어서 이름 음절 수와 무관하게 통째로 샜다(직접 확인).


@pytest.mark.parametrize(
    "text, name",
    [
        ("이력서 접수: 전혜호, 생일 1986-10-02", "전혜호"),
        ("면허 갱신 신청: 최예도, 면허번호 17-82-67", "최예도"),
        ("이력서 접수: 유성진, 생일 1957-06-14", "유성진"),
        ("이력서 접수: 홍인연, 생일 2005-03-27", "홍인연"),
        ("이력서 접수: 오민군, 생일 1958-04-27", "오민군"),
        ("이력서 접수: 이정수, 생일 1972-02-15", "이정수"),
        ("면허 갱신 신청: 유아호, 면허번호 22-01-58", "유아호"),
        ("이력서 접수: 문석율, 생일 2000-06-21", "문석율"),
        ("면허 갱신 신청: 손은, 면허번호 22-01-58", "손은"),  # 2음절 이름도 라벨만 있으면 잡힌다
    ],
)
def test_document_title_labels_before_a_comma_separated_tail(text, name):
    assert name in names(text)


def test_document_title_label_still_needs_a_colon_or_bar():
    # 같은 라벨 문구라도 콜론·세로줄 없이 문장 속에 그냥 등장하면 이름 단서로 삼지 않는다
    # (다른 템플릿 "지원자 {name} 이력서 접수 — 연락처 {phone}"과 헷갈리지 않기 위해)
    assert names("지원자 김민수 이력서 접수 — 연락처 010-1234-5678") == ["김민수"]


# ── 표(CSV·TSV·마크다운) 머리행 열 이름(#526) ─────────────────────────
# 같은 줄 라벨(위 테스트들)은 "성명: 홍길동"처럼 라벨과 값이 한 줄에 있어야 잡는다. 고객
# 명단·수신자 목록처럼 머리행에 열 이름만 있고 값은 아래 행에 나열되는 표는 그래서 못
# 잡았다 — 전화번호·이메일은 가려지고 이름만 원문 그대로 남는 문제였다.


def test_csv_name_column_is_masked_for_every_row():
    text = (
        "이름,전화번호,이메일\n"
        "김민수,010-1234-5678,minsu@example.com\n"
        "이영희,010-2345-6789,younghee@example.com\n"
        "박철수,010-3456-7890,cheolsu@example.com"
    )
    assert names(text) == ["김민수", "이영희", "박철수"]


def test_tsv_name_column_is_masked():
    text = "성명\t부서\t연락처\n김민수\t영업팀\t010-1234-5678\n이영희\t개발팀\t010-2345-6789"
    assert names(text) == ["김민수", "이영희"]


def test_markdown_table_name_column_is_masked():
    text = "| 이름 | 연락처 |\n|---|---|\n| 김민수 | 010-1234-5678 |\n| 이영희 | 010-2345-6789 |"
    assert names(text) == ["김민수", "이영희"]


def test_single_row_csv_with_a_name_column():
    assert names("고객명,주소\n김민수,서울시 강남구") == ["김민수"]


def test_quoted_csv_cell_is_still_read_as_a_name():
    # 따옴표로 감싼 칸("김민수") 안쪽만 값으로 삼는다. 다른 칸의 따옴표 안 쉼표("인사팀,
    # 신규")를 열 구분자로 착각해 칸 수가 어긋나면 표 전체를 못 읽는다 — 실제 CSV 규칙대로
    # 파싱해야 한다.
    text = '이름,메모\n"김민수","인사팀, 신규"'
    assert names(text) == ["김민수"]


@pytest.mark.parametrize(
    "text",
    [
        "연락처,이름\n010-1234-5678,김민수",  # 이름 열이 끝
        "순번,이름,연락처\n1,김민수,010-1234-5678",  # 이름 열이 가운데
    ],
)
def test_name_column_at_any_position(text):
    assert "김민수" in names(text)


def test_header_that_is_not_a_name_column_is_not_newly_matched():
    # 대조군: 머리행 열 이름이 이름 계열 라벨이 아니면(구분·내용) 아래 값을 새로 잡지 않는다
    assert names("구분,내용\n일반,회의록") == []


def test_table_ends_at_a_blank_line():
    # 표 탐지(뒤에 실행)와 일반 규칙(먼저 실행)은 서로 다른 순서로 결과를 쌓으므로, 등장
    # 순서가 아니라 집합으로 비교한다 — 최종 파이프라인은 위치로 다시 정렬한다.
    text = (
        "이름,연락처\n김민수,010-1234-5678\n\n"
        "이건 표가 아닌 일반 문장이고 성명 이철수 님이 등장합니다"
    )
    assert set(names(text)) == {"김민수", "이철수"}


def test_table_ends_when_a_row_has_a_different_column_count():
    text = "이름,연락처\n김민수,010-1234-5678\n이거는칸이하나뿐"
    assert names(text) == ["김민수"]


def test_row_whose_name_cell_equals_a_label_is_skipped_not_a_false_positive():
    # 값 자리에 다른 라벨이 왔다("성명,전화번호") — 이름으로 잡지 않고, 표는 계속 읽는다
    text = "이름,연락처\n성명,전화번호\n김민수,010-1234-5678"
    assert names(text) == ["김민수"]


def test_large_csv_roster_stays_linear():
    import time

    def seconds(n: int) -> float:
        rows = "\n".join(f"성명{i}본,010-1234-{i:04d}" for i in range(n))
        text = "이름,연락처\n" + rows
        start = time.perf_counter()
        NameDetector().detect(text)
        return time.perf_counter() - start

    seconds(200)
    small, large = seconds(2000), seconds(8000)
    assert large < 8 * small + 0.1  # 선형이면 약 4배, 제곱이면 약 16배
