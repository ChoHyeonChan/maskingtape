# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

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


def test_name_ending_in_yang_or_gun_is_not_leaked():
    # #340: 끝음절이 양/군인 실명("김하양"·"박도군")에서 그 글자를 존칭으로 오인해 이름에서
    # 떼어내면 그 글자가 원문 노출된다(미탐=유출). 이름에 포함해 통째로 가린다(더 가리기=안전).
    assert detect("고객 김하양님께 안내")[0].text == "김하양"
    assert detect("환자 박도군 내원 예정")[0].text == "박도군"


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


def test_department_word_with_particle_does_not_bypass_title_guard():
    # #247: 부서·업무어(2자) 뒤에 조사가 붙어 3자로 보여도(정기가=정기+가) 이름이 아니다.
    assert detect("대표 정기가 참석했습니다") == []
    assert detect("부장 구매가 결재를 승인") == []
    # 유출 방지: 실명은 조사로 끝나도(김지은) stem이 부서어가 아니라 그대로 잡히고,
    # 부서 stem이어도 조사 아닌 글자로 끝나면(정기훈) 실명으로 잡힌다.
    assert detect("대표 정기훈 참석")[0].text == "정기훈"
    assert detect("대표 김지은 확인")[0].text == "김지은"


# ─── #394 규칙판 정비: 역할어·직함 어휘, 조사, 라벨 단어, 실명 유출 ───────────────


def test_common_titles_from_real_documents_are_cues():
    # #394: 실무 문서에서 흔한 직함이 어휘에 없어 풀네임도 통째로 새어나갔다. 앞·뒤 모두 잡는다.
    for title in ("총무", "매니저", "상무", "국장", "지점장", "간호사", "변호사", "회계사", "인턴", "팀원"):
        assert [d.text for d in detect(f"{title} 김하늘이 참석했습니다.")] == ["김하늘"], title
        assert [d.text for d in detect(f"김하늘 {title} 참석")] == ["김하늘"], title
    # "부사장"은 "사장"의 부분 문자열로 우연히 잡히던 것 — 정식 항목이라 앞에서도 잡힌다.
    assert [d.text for d in detect("부사장 박서준이 참석했습니다.")] == ["박서준"]
    # 직함만 단서일 땐 2음절 이름을 일부러 놓치는 설계(#213/#239)는 그대로다.
    assert detect("총무 김민, 참석") == []


def test_form_labels_before_a_name_are_cues():
    # 서식의 사람 칸 라벨 — 벤치 미탐의 절반 이상이 이 어휘 부족이었다.
    assert [d.text for d in detect("환자명 오훈, 주민번호 확인")] == ["오훈"]
    assert [d.text for d in detect("명의자 양규하, 연락처 010-1234-5678")] == ["양규하"]
    assert [d.text for d in detect("전입신고 대상자: 윤은성, 신주소 대구")] == ["윤은성"]
    assert [d.text for d in detect("신규 채용자 김우, 운전면허번호는")] == ["김우"]
    assert [d.text for d in detect("학생 김정규(학부모 연락처 010-1234-5678)")] == ["김정규"]
    # 역할어 + 존칭이면 0.75 — "민원인"은 전엔 그 자체가 민+원인으로 오탐되던 단어다.
    found = detect("민원인 양민지님, 주민등록번호 확인")
    assert [(d.text, d.confidence) for d in found] == [("양민지", 0.75)]


def test_particle_after_a_cue_does_not_break_the_cue():
    # "담당자는 X", "예금주는 X" — 조사 하나 때문에 단서를 통째로 잃고 있었다.
    assert [d.text for d in detect("담당자는 서정호입니다.")] == ["서정호"]
    assert [d.text for d in detect("예금주는 고혜입니다.")] == ["고혜"]
    assert [d.text for d in detect("서명자는 임진입니다.")] == ["임진"]
    assert [d.text for d in detect("담당자가 손인은에서 변경되었습니다")] == ["손인은"]


def test_ip_of_imnida_is_not_swallowed_into_two_char_name():
    # "입니다"의 "입"은 이름 끝음절로 쓰이지 않는다 — 2음절 이름 뒤에 붙어도 이름에 넣지 않는다.
    assert [d.text for d in detect("예금주는 고혜입니다.")] == ["고혜"]
    assert [d.text for d in detect("고객 김민을 안내했습니다")] == ["김민"]


def test_real_names_sharing_a_prefix_with_a_label_word_are_not_leaked():
    # 예전엔 "이용"·"이유"를 startswith로 걸러 실명 이용재·이유진이 통째로 새어나갔다(유출).
    assert [(d.text, d.confidence) for d in detect("고객 이유진님 연락 바랍니다")] == [("이유진", 0.75)]
    assert [d.text for d in detect("담당자 이용재입니다")] == ["이용재"]
    # 라벨 단어 자체는 여전히 이름이 아니다.
    assert detect("고객 이용 안내를 드립니다") == []
    assert detect("이유가 무엇인가요") == []


def test_label_word_after_a_cue_hands_the_cue_to_the_next_name():
    # "신청자 성명 김하늘" — 예전엔 "성명"을 이름으로 오탐하고 정작 "김하늘"은 단서를 잃어 놓쳤다.
    assert [d.text for d in detect("신청자 성명 김하늘")] == ["김하늘"]
    assert [d.text for d in detect("고객 이름 김하늘")] == ["김하늘"]
    assert detect("신청자 성명, 주소를 적으세요") == []


def test_common_two_syllable_nouns_next_to_a_cue_are_not_names():
    # 성씨로 시작하는 흔한 일반명사 — 역할어·직함 옆에 오면 이름처럼 보인다.
    for text in (
        "고객 문의 접수", "고객 서류 제출", "고객 지원 담당", "작성자 정보를 확인하세요",
        "대표 차량이 배정되었습니다", "부장 성과가 좋았습니다", "팀장 안내가 시작되었습니다",
        "대표 허가가 필요합니다", "담당자 최근 변경",
    ):
        assert detect(text) == [], text
    # 같은 두 글자로 시작해도 글자가 더 이어지면 실명일 수 있어 그대로 잡는다(단어 경계).
    assert [d.text for d in detect("대표 정기훈 참석")] == ["정기훈"]
    assert [d.text for d in detect("작성자 정보라 확인")] == ["정보라"]
