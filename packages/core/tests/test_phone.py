# SPDX-License-Identifier: Apache-2.0

"""전화번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다."""

from maskingtape.detectors import PhoneDetector


def detect(text: str):
    return PhoneDetector().detect(text)


def test_detects_mobile_with_hyphen():
    found = detect("연락처는 010-1234-5678 입니다")
    assert len(found) == 1
    assert found[0].kind == "phone"
    assert found[0].text == "010-1234-5678"
    assert found[0].confidence == 1.0


def test_detects_bare_mobile_with_lower_confidence():
    # 구분자 없는 숫자열은 다른 번호일 수도 있으니 확신도만 낮춘다
    found = detect("01012345678")
    assert len(found) == 1
    assert found[0].confidence < 1.0


def test_detects_international_format():
    found = detect("+82-10-1234-5678 로 전화주세요")
    assert len(found) == 1


def test_detects_seoul_landline():
    found = detect("사무실 02-123-4567")
    assert len(found) == 1


def test_detects_internet_phone():
    found = detect("070-1234-5678")
    assert len(found) == 1


def test_detects_050x_personal_numbers():
    # 050X 평생번호·안심번호는 실번호를 숨기는 개인 연락처라 개인정보다 (미탐=유출)
    for number in ("0507-1234-5678", "0505-123-4567", "050-1234-5678"):
        found = detect(f"연락처 {number}")
        assert len(found) == 1, number
        assert found[0].text == number


def test_detects_separator_variants_that_previously_leaked():
    # 미탐=유출: 표 붙여넣기·자동서식에서 그룹 사이에 "공백-하이픈-공백"·이중공백·en-dash가
    # 끼면 전화번호가 통째로 새던 문제.
    for variant in (
        "연락 010 - 1234 - 5678",  # 공백-하이픈-공백
        "연락 010  1234  5678",  # 이중 공백
        "연락 010 – 1234 – 5678",  # en-dash(–)
    ):
        found = detect(variant)
        assert len(found) == 1, variant
        assert found[0].text.replace(" ", "").replace("–", "").replace("-", "") == "01012345678", variant


def test_rejects_non_phone_numbers():
    # 전화번호 형태가 아닌 숫자열은 잡지 않는다
    assert detect("가격은 1234-5678원") == []
    assert detect("주문번호 20260718") == []


# --- 괄호 표기 (#397) ---
# 국번을 괄호로 감싸는 표기는 명함·문서 서식에서 흔하다.
# 여는 괄호가 있으면 닫는 괄호도 있어야 통과한다(정규식 조건부 참조).


def test_detects_mobile_in_parentheses():
    found = detect("연락처 (010) 1234-5678 입니다")
    assert len(found) == 1
    assert found[0].text == "(010) 1234-5678"
    assert found[0].confidence == 1.0  # 구분자가 있어 확신도 최대


def test_detects_mobile_in_parentheses_without_space():
    found = detect("(010)1234-5678")
    assert len(found) == 1
    assert found[0].text == "(010)1234-5678"


def test_detects_landline_in_parentheses():
    # 서울 02와 광역 지역번호 3자리 모두
    for text, expected in [("(02) 123-4567", "(02) 123-4567"), ("(031) 123-4567", "(031) 123-4567")]:
        found = detect(text)
        assert len(found) == 1, f"{text!r} 미탐지"
        assert found[0].text == expected


def test_parenthesis_form_keeps_existing_formats_working():
    # 괄호 지원을 넣어도 기존 표기가 그대로 잡혀야 한다
    for text in ["010-1234-5678", "01012345678", "+82 10-1234-5678", "02-123-4567"]:
        assert len(detect(text)) == 1, f"{text!r} 회귀"


def test_does_not_treat_year_in_parentheses_as_phone():
    """`(2024) 1234-5678` 같은 연도 표기를 전화번호로 잡지 않는다.

    괄호 안이 국번 패턴(01X / 02 / 0NN / 070 / 050X)일 때만 통과하므로,
    괄호를 허용해도 오탐 범위가 넓어지지 않는다.
    """
    for text in ["(2024) 1234-5678", "(999) 1234-5678", "(123) 456-7890"]:
        assert detect(text) == [], f"{text!r}는 전화번호가 아니다"


def test_open_parenthesis_only_still_detects_the_number_itself():
    """여는 괄호만 있으면 괄호를 뺀 번호로 잡는다.

    `(010 1234-5678`은 괄호가 없어도 유효한 번호라 그대로 탐지된다.
    괄호는 매치 시작 전이라 범위에 들어오지 않는다.
    """
    found = detect("(010 1234-5678")
    assert len(found) == 1
    assert found[0].text == "010 1234-5678"


def test_closing_parenthesis_only_is_a_known_miss():
    """알려진 한계 — 닫는 괄호만 있는 깨진 표기는 잡지 못한다.

    `)`가 구분자 목록에 없어 국번 뒤에서 매치가 끊긴다. 구분자에 `)`를 넣으면
    괄호 쌍 검사가 무의미해지므로 넣지 않았다. 실무에서 닫는 괄호만 쓰는 표기는
    드물다. 현재 동작을 여기 고정한다.
    """
    assert detect("010) 1234-5678") == []
