"""이름 탐지기 테스트 — 모든 이름은 합성(가짜)이다."""

from maskingtape.detectors import NameDetector


def detect(text: str):
    return NameDetector().detect(text)


def test_detects_name_with_prefix_and_suffix_at_high_confidence():
    found = detect("고객 김철수님 010-1234-5678로 연락주세요")
    assert len(found) == 1
    assert found[0].kind == "name"
    assert found[0].text == "김철수"
    assert found[0].confidence == 0.75


def test_detects_name_with_prefix_only_at_lower_confidence():
    found = detect("신청자: 박서연 / 연락처: 010-1234-5678")
    assert len(found) == 1
    assert found[0].text == "박서연"
    assert found[0].confidence == 0.5


def test_detects_name_with_suffix_only_at_lower_confidence():
    found = detect("최민 환자분, 주민등록번호 확인되었습니다")
    assert len(found) == 1
    assert found[0].text == "최민"
    assert found[0].confidence == 0.5


def test_ignores_surname_like_word_without_any_context_cue():
    # 문맥 단서(역할어/존칭)가 전혀 없으면 그냥 흔한 단어와 구분이 안 되므로 버린다
    assert detect("김치찌개를 먹었다") == []


def test_self_introduction_prefix():
    found = detect("안녕하세요, 저는 정하늘이고 전화번호는 010-1234-5678입니다")
    assert len(found) == 1
    assert found[0].text == "정하늘"


def test_ignores_domain_label_words_that_start_with_a_surname():
    # "주민번호"(주+민번), "전화번호"(전+화번), "이메일"(이+메일)은 성씨로 시작하는 흔한 단어라
    # 역할어 바로 뒤에 와도 이름으로 오탐하면 안 된다.
    assert detect("고객 주민번호 800101-1234560 확인 부탁드립니다") == []
    assert detect("고객 전화번호는 010-1234-5678입니다") == []
    assert detect("신청자: 이메일로 회신 부탁드립니다") == []


def test_does_not_swallow_honorific_into_two_char_name():
    # #147: 성씨+1글자 이름 뒤에 붙은 존칭을 이름으로 삼키지 않는다 — 스팬은 "심진", 님은 존칭
    found = detect("고객 심진님 연락 부탁드립니다")
    assert len(found) == 1
    assert found[0].text == "심진"
    assert found[0].confidence == 0.75  # 역할어 + 존칭 둘 다 → 높은 확신도


def test_does_not_swallow_ssi_honorific_without_space():
    found = detect("고객 최민씨 확인 바랍니다")
    assert found[0].text == "최민"


def test_preserves_legit_two_char_name_before_honorific():
    # 존칭 양보가 정당한 2글자 이름("이도")을 깨면 안 된다 — 이름은 "이도", 님은 존칭
    found = detect("환자 이도님께 안내드립니다")
    assert len(found) == 1
    assert found[0].text == "이도"


def test_preserves_two_char_name_when_no_honorific_follows():
    # "도"는 존칭이 아니므로 "박도"는 그대로 2글자 이름으로 유지된다
    found = detect("박도 담당자에게 전달")
    assert found[0].text == "박도"


def test_does_not_match_surname_in_middle_of_word():
    # #158: "감지되어"의 "지"(성씨 사전)가 단어 중간이라 이름 후보가 되면 안 된다.
    # 오탐 "지되어"가 사라지고, 뒤의 진짜 이름 "양빈도"가 대신 잡혀야 한다.
    found = detect("카드 결제가 감지되어 양빈도님께 확인 연락드립니다")
    assert [d.text for d in found] == ["양빈도"]


def test_recovers_real_name_previously_swallowed_by_midword_fp():
    # #158: 단어 중간 오탐이 뒤 이름의 첫 글자를 존칭으로 삼키던 문제 — 이제 진짜 이름을 잡는다.
    found = detect("이상 거래가 감지되어 양연준님께 안내드립니다")
    assert [d.text for d in found] == ["양연준"]
