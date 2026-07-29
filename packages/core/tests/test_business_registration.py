"""사업자등록번호 탐지기 테스트 — 모든 번호는 합성(가짜)이다.

여기 쓰는 번호는 국세청 검증 알고리즘의 체크섬만 맞춘 가짜로, 실제 등록부와 무관하다.
알고리즘 자체는 공개된 사업자번호(영수증에 찍히는 공개정보)로 별도 교차검증했다.
"""

from maskingtape.detectors import BusinessRegistrationDetector


def detect(text: str):
    return BusinessRegistrationDetector().detect(text)


def test_detects_valid_business_number():
    found = detect("사업자등록번호 123-45-67800 확인 바랍니다")
    assert len(found) == 1
    assert found[0].kind == "biz_reg"
    assert found[0].text == "123-45-67800"
    assert found[0].confidence == 1.0


def test_detects_valid_number_in_contract_sentence():
    # 계약서형 문장에서 사업자번호만 잡는다(이름·상호는 다른 탐지기 소관)
    found = detect("공급자 마스킹테이프 999-88-87705 로 표기")
    assert len(found) == 1
    assert found[0].text == "999-88-87705"
    assert found[0].confidence == 1.0


def test_rejects_checksum_failure():
    # 형태는 3-2-5지만 체크섬이 틀린 번호는 사업자번호가 아니다 — 버린다(오탐 방지).
    # 사업자번호는 예외 없이 체크섬이 있으므로 체크섬이 곧 판별 기준이다.
    assert detect("번호 123-45-67890 입니다") == []  # 67890은 검증자리 불일치
    assert detect("코드 567-27-70901 참조") == []     # bench에서 오탐되던 난수


def test_rejects_other_number_groupings():
    # 3-2-5가 아닌 묶음은 사업자번호 표기가 아니다
    assert detect("010-1234-5678") == []          # 전화(3-4-4)
    assert detect("주민 800101-1234560") == []     # 주민번호(6-7)
    assert detect("4242-4242-4242-4242") == []    # 카드(4-4-4-4)


def test_does_not_grab_digits_from_a_longer_run():
    # 앞뒤에 숫자가 더 붙은 긴 숫자열의 일부를 오려내지 않는다
    assert detect("9123-45-678009") == []
    assert detect("00123-45-67800") == []


def test_detects_multiple_numbers():
    found = detect("공급자 123-45-67800 / 공급받는자 101-20-34500")
    assert len(found) == 2
    assert {f.text for f in found} == {"123-45-67800", "101-20-34500"}
