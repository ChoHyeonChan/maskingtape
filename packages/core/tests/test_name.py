"""이름 탐지기 테스트 — 모든 이름은 합성(가짜)이다."""

from maskingtape.detectors.name import NameDetector


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
