# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""주소 꼬리(층·호·건물명·참고항목)와 시작점 없는 건물 단위 주소 — 합성 데이터만 사용(#593·#605)."""

import pytest

from maskingtape.detectors import AddressDetector


def spans(text: str) -> list[str]:
    return [d.text for d in AddressDetector().detect(text)]


# ── #605: 시작점은 있는데 층·호·건물명·참고항목이 원문으로 남던 표기 ──


@pytest.mark.parametrize(
    "text, expected",
    [
        ("서울특별시 강남구 테헤란로 123 4층 401호", "서울특별시 강남구 테헤란로 123 4층 401호"),
        ("서울특별시 강남구 테헤란로 123, 3층", "서울특별시 강남구 테헤란로 123, 3층"),
        ("서울특별시 강남구 테헤란로 123 지하 1층", "서울특별시 강남구 테헤란로 123 지하 1층"),
        ("서울 강남구 테헤란로 123 삼성빌딩 5층", "서울 강남구 테헤란로 123 삼성빌딩 5층"),
        ("서울특별시 마포구 월드컵북로 396 누리꿈스퀘어 12층", "서울특별시 마포구 월드컵북로 396 누리꿈스퀘어 12층"),
        (
            "부산광역시 해운대구 센텀중앙로 79 센텀사이언스파크 1203호",
            "부산광역시 해운대구 센텀중앙로 79 센텀사이언스파크 1203호",
        ),
        ("경기 성남시 분당구 판교역로 235 H스퀘어 N동 7층", "경기 성남시 분당구 판교역로 235 H스퀘어 N동 7층"),
        ("인천 연수구 송도동 12-3 더샵퍼스트월드 A동 2101호", "인천 연수구 송도동 12-3 더샵퍼스트월드 A동 2101호"),
        ("서울특별시 강남구 테헤란로 123 (역삼동)", "서울특별시 강남구 테헤란로 123 (역삼동)"),
        (
            "서울특별시 강남구 테헤란로 123, 4층 401호(역삼동, 더샵아파트)",
            "서울특별시 강남구 테헤란로 123, 4층 401호(역삼동, 더샵아파트)",
        ),
        ("서울특별시 강남구 테헤란로 123 B1 101호", "서울특별시 강남구 테헤란로 123 B1 101호"),
        ("서울특별시 강남구 테헤란로 123 새솔빌딩 가동 3층", "서울특별시 강남구 테헤란로 123 새솔빌딩 가동 3층"),
    ],
)
def test_address_tail_keeps_floor_unit_building_and_reference(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text, expected",
    [
        # 지금도 끝까지 가리던 표기(대조)
        ("서울특별시 강남구 테헤란로 123 더샵아파트 101동 1203호", "서울특별시 강남구 테헤란로 123 더샵아파트 101동 1203호"),
        ("서울특별시 강남구 테헤란로 123, 101호", "서울특별시 강남구 테헤란로 123, 101호"),
        # 층 뒤 조사
        ("서울특별시 강남구 테헤란로 123 4층에 있습니다", "서울특별시 강남구 테헤란로 123 4층"),
    ],
)
def test_address_tail_controls(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("한빛아파트 101-1203호로 보내 주세요", "한빛아파트 101-1203호"),
        ("서울특별시 강남구 테헤란로 123 101-1203", "서울특별시 강남구 테헤란로 123 101-1203"),
        ("한빛아파트 101동1203호", "한빛아파트 101동1203호"),
        ("한빛오피스텔 1203호", "한빛오피스텔 1203호"),
        ("서울특별시 강남구 테헤란로 123 4F", "서울특별시 강남구 테헤란로 123 4F"),
        # 지금도 끝까지 가리던 표기(대조)
        ("한빛아파트 101동 1203호", "한빛아파트 101동 1203호"),
        ("서울특별시 강남구 테헤란로 123 4층 401호", "서울특별시 강남구 테헤란로 123 4층 401호"),
    ],
)
def test_address_tail_keeps_compact_unit_forms(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text, expected",
    [
        # 건물 종류 낱말에 붙은 '동'("한빛타워동")에서 끊겨 "동 1203호 12층 (역삼동)"이 남던 표기
        (
            "서울특별시 강남구 테헤란로 123 한빛타워동 1203호 12층 (역삼동)",
            "서울특별시 강남구 테헤란로 123 한빛타워동 1203호 12층 (역삼동)",
        ),
        ("서울특별시 강남구 역삼동 123-45 한빛타워동 1203호", "서울특별시 강남구 역삼동 123-45 한빛타워동 1203호"),
        ("서울특별시 강남구 테헤란로 123 한빛타워동1203호", "서울특별시 강남구 테헤란로 123 한빛타워동1203호"),
        ("서울특별시 강남구 테헤란로 123 의료센터동 3층", "서울특별시 강남구 테헤란로 123 의료센터동 3층"),
        ("한빛타워동 1203호로 보내 주세요", "한빛타워동 1203호"),
        # 호 뒤에 층을 쓰는 표기
        ("서울특별시 강남구 역삼동 123-45 한빛타워 1203호 12층", "서울특별시 강남구 역삼동 123-45 한빛타워 1203호 12층"),
        ("한빛오피스텔 1203호 12층", "한빛오피스텔 1203호 12층"),
    ],
)
def test_address_tail_keeps_glued_building_dong_and_floor_after_unit(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text, expected",
    [
        # 건물명에 붙은 '동'은 뒤에 층·호가 올 때만 받는다.
        ("서울특별시 강남구 테헤란로 123 한빛센터동 앞에서", "서울특별시 강남구 테헤란로 123 한빛센터"),
        ("서울특별시 강남구 테헤란로 123 한빛타워 동쪽 출입구", "서울특별시 강남구 테헤란로 123 한빛타워"),
    ],
)
def test_glued_building_dong_needs_floor_or_unit(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text, expected",
    [
        # 목록에 없는 건물명은 뒤에 층·동·호가 올 때만 받는다 — 평범한 낱말을 삼키지 않는다.
        ("서울특별시 강남구 테헤란로 123 근처에서 만나요", "서울특별시 강남구 테헤란로 123"),
        ("서울특별시 강남구 테헤란로 123 앞 카페", "서울특별시 강남구 테헤란로 123"),
        # 한글 차례 동("가동")은 뒤에 층·호가 있을 때만 — "자동"·"아동" 같은 낱말과 헷갈리지 않게.
        ("서울특별시 강남구 테헤란로 123 자동 결제", "서울특별시 강남구 테헤란로 123"),
        # 괄호 안이 동 이름이 아니면 참고항목으로 보지 않는다.
        ("서울특별시 강남구 테헤란로 123 (본사)", "서울특별시 강남구 테헤란로 123"),
        # 지하층 표기(B1)처럼 생겼어도 영문자가 이어지면 낱말의 일부다.
        ("서울특별시 강남구 테헤란로 123 B2B 영업팀", "서울특별시 강남구 테헤란로 123"),
    ],
)
def test_address_tail_does_not_swallow_plain_words(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text",
    [
        "한빛아파트 3-4호선 환승",
        "오피스텔 2호점 오픈",
        "4F 회의실",
    ],
)
def test_compact_unit_forms_need_address_or_real_unit(text):
    assert spans(text) == []


# ── #593: 시/도·도로명 없이 건물명 + 동·층 + 호만 쓴 주소 ──


@pytest.mark.parametrize(
    "text, expected",
    [
        ("한빛아파트 101동 302호로 보내 주세요.", "한빛아파트 101동 302호"),
        ("새솔빌라 2동 201호 사시는 분이죠?", "새솔빌라 2동 201호"),
        ("배송지는 푸른오피스텔 12층 1203호입니다", "푸른오피스텔 12층 1203호"),
        ("한빛맨션 A동 101호", "한빛맨션 A동 101호"),
    ],
)
def test_building_unit_without_road_address_is_masked(text, expected):
    assert spans(text) == [expected]


@pytest.mark.parametrize(
    "text",
    [
        "한빛아파트 앞에서 만나요",  # 동·호가 없다
        "한빛아파트 101동 앞 놀이터",  # 호가 없다
        "새로 지은 아파트 3채가 분양됐다",  # 건물명이 아니다
        "역삼동 12번지 근처",  # 건물 단위가 아니다(시작점 없는 지번은 이 규칙의 대상이 아니다)
    ],
)
def test_building_unit_needs_building_and_unit(text):
    assert spans(text) == []


# ── 꼬리가 뒤의 다른 개인정보를 삼켜 종류가 숨지 않게 ──
# 가리는 글자는 같아도, 주소가 번호·이름을 품으면 scan 결과에서 rrn·phone·name이 사라진다.
# 웹은 종류마다 가림·보임을 바꿀 수 있어서 "주소"를 풀면 안의 번호도 같이 풀린다(#172와 같은 모양).


@pytest.mark.parametrize(
    "text, address, other_kind, other_text",
    [
        (
            "서울특별시 강남구 테헤란로 123 (역삼동, 8001011234560)",
            "서울특별시 강남구 테헤란로 123",
            "rrn",
            "8001011234560",
        ),
        (
            "서울특별시 강남구 테헤란로 123 (역삼동, 01012345678)",
            "서울특별시 강남구 테헤란로 123",
            "phone",
            "01012345678",
        ),
        ("서울특별시 강남구 테헤란로 123 홍길동님 3층", "서울특별시 강남구 테헤란로 123", "name", "홍길동"),
    ],
)
def test_address_tail_does_not_swallow_other_pii(text, address, other_kind, other_text):
    from maskingtape import Pipeline

    found = [(d.kind, d.text) for d in Pipeline().scan(text)]
    assert ("address", address) in found
    assert (other_kind, other_text) in found
