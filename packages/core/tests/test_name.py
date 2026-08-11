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


def test_detects_name_with_job_title_suffix():
    # #213: 업무·계약 문서의 "이름 + 직함" — 직함이 이름과 존칭 사이에 껴도 이름을 잡는다.
    found = detect("홍길동 대표가 서명했다")
    assert [d.text for d in found] == ["홍길동"]
    assert found[0].confidence == 0.5
    # 직함 뒤에 존칭이 더 붙어도(부장님) 이름 스팬은 이름만
    assert detect("김민수 부장님께 전달")[0].text == "김민수"


def test_department_word_before_title_is_not_a_name():
    # #213: 부서·업무어(2자)가 직함 앞에 오는 건 이름이 아니다 — 직함만 단서일 땐 성+2자(3글자)를 요구.
    assert detect("구매 부장에게 문의") == []
    assert detect("정기 이사회 안건 상정") == []
    assert detect("홍보 팀장 회의록") == []


def test_two_char_name_with_title_only_is_dropped_by_design():
    # #213 트레이드오프: 직함만 단서인 2글자 이름("김민 대표")은 부서어와 구분이 안 돼 규칙에선 버린다.
    # 문맥을 이해하는 하이브리드(LLM)판이 이런 경우를 담당한다.
    assert detect("김민 대표 서명") == []
    # 단, 존칭(님)이 붙으면 2글자 이름도 그대로 잡는다 — 님은 강한 단서라 3글자 제약을 안 건다.
    assert detect("김민님 안내")[0].text == "김민"


def test_detects_name_with_title_prefix():
    # #239: 직함이 이름 앞에 오는 형태("대표 홍길동", "부장 김철수")도 잡는다.
    assert detect("대표 홍길동이 서명했다")[0].text == "홍길동"
    assert detect("부장 김철수 확인")[0].text == "김철수"
    assert detect("사장 이영수")[0].text == "이영수"


def test_title_prefix_before_department_word_is_not_a_name():
    # #239: 직함 뒤에 부서·업무어가 오면 이름이 아니다. 2자 부서어는 3자 가드로,
    # "대표이사"가 띄어쓰기된 "대표 이사가/이사회"는 '이사'를 비이름 단어로 막는다.
    assert detect("대표 이사회 안건 상정") == []
    assert detect("대표 이사가 참석했다") == []
    assert detect("구매 부장에게 문의") == []
