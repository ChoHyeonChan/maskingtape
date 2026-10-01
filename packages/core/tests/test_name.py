# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 탐지기 테스트 — 모든 이름은 합성(가짜)이다."""

import pytest

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


def test_strong_cues_exempt_common_word_stopwords():
    # 정지어에는 2음절 실명과 겹치는 말이 있다(문서·조정·이상·유지·양성…). 앞뒤 단서가 둘 다
    # 있는 강한 경우까지 버리면 실명을 놓친다 — 미탐은 곧 유출이라 그때만 면제한다(#446 리뷰).
    assert [d.text for d in detect("고객 이상 씨 확인")] == ["이상"]
    assert [d.text for d in detect("신청자 조정 님 확인")] == ["조정"]
    assert [d.text for d in detect("작성자 문서 님")] == ["문서"]
    # 단서가 한쪽뿐인 약한 경우엔 오탐이 더 위험하므로 그대로 버린다.
    assert detect("대표 차량이 배정되었습니다") == []
    assert detect("부장 성과가 좋았습니다") == []
    assert detect("고객 문의 접수") == []


def test_label_words_are_dropped_even_with_strong_cues():
    # 라벨 단어(성명·전화번호…)는 서식 라벨이라 앞뒤 단서가 다 붙어도 이름이 아니다.
    assert detect("작성자 성명 님") == []
    assert detect("담당자 전화번호 님") == []
    assert detect("고객 생년월일 씨") == []


def test_cue_words_followed_by_an_honorific_are_not_names():
    # #450: 호칭 단어의 첫 글자가 성씨 사전에 있으면("고"객·"원"장·"차"장…) 뒤의 "님"과
    # 함께 "성+이름 + 존칭"으로 읽혀 호칭 자체가 이름으로 잡혔다.
    for text in (
        "고객님께 안내드립니다.",
        "원장님께 안내드립니다.",
        "차장님께 보고드립니다.",
        "강사님께 여쭙니다.",
        "신청자님께 안내드립니다.",
        "민원인님께 회신드립니다.",
    ):
        assert detect(text) == [], f"호칭이 이름으로 잡힘: {text!r}"


def test_real_names_that_start_like_a_cue_word_are_still_detected():
    # 호칭과 완전히 같을 때만 버린다. 호칭 글자로 시작하는 실명("원장훈")은 그대로 잡는다.
    assert [d.text for d in detect("고객 원장훈님께 안내드립니다.")] == ["원장훈"]
    assert [d.text for d in detect("원장 김철수님께 보고드립니다.")] == ["김철수"]
    # 호칭이 버려져도 바로 뒤의 실명은 놓치지 않는다.
    assert [d.text for d in detect("고객님 김철수 씨 확인 바랍니다.")] == ["김철수"]


# ── 0.5짜리(약한 단서) 오탐 — 저장소 문서 실측(#484) ─────────────────
# 규칙 모드는 앞뒤 단서 중 한쪽만 있어도 확신도 0.5로 이름을 잡는다. 합성 벤치에서는 이
# 0.5짜리가 대부분 실명이었지만, 저장소 문서 같은 평범한 글에서는 40건 중 22건이 이름이
# 아니었다 — 아래 4가지 패턴이 원인이었다.


@pytest.mark.parametrize(
    "text",
    [
        "이름 정밀 탐지는 로컬 LLM을 켜야 한다.",  # "이름" 단서 뒤 일반 낱말
        "이름은 문맥 판단이 필요하다.",
        "이름은 전혀 안 가린다.",
        "이름 하이브리드 모드",  # 낱말 중간에서 끊김("하이브"만 잘라 잡음)
        "050 정규식 양쪽에 경계를 둔다.",  # 호칭 "양"으로 시작하는 낱말("양쪽")
        "SBOM 공식 양식과 같다.",  # 호칭 "양"으로 시작하는 낱말("양식")
        "이전엔 팀장이 결정했다.",  # 직함 앞 부사("이전"+조사 "엔")
    ],
)
def test_weak_cue_false_positives_from_plain_documents_are_not_names(text):
    assert detect(text) == [], f"오탐: {text!r} -> {detect(text)}"


def test_weak_cue_false_positive_fixes_do_not_drop_real_names():
    # 위 4가지 원인을 고치면서 진짜 이름까지 놓치면 그게 더 큰 문제다(미탐=유출).
    assert [d.text for d in detect("담당자 박서연 확인 부탁드립니다.")] == ["박서연"]
    assert [d.text for d in detect("담당자는 서정호입니다.")] == ["서정호"]
    assert [d.text for d in detect("서명자는 임진입니다.")] == ["임진"]
    assert [d.text for d in detect("김민지 양이 접수했습니다.")] == ["김민지"]
    assert [d.text for d in detect("고객 김철수님 010-1234-5678로 연락주세요")] == ["김철수"]
    # "에게"·"에서"처럼 "에"로 시작하는 두 글자 조사 뒤의 이름도 그대로 잡혀야 한다 —
    # 낱말 경계 확인(#484)을 더하면서 단일 글자 조사 목록만 참고하면 이런 조사를 놓친다.
    assert [d.text for d in detect("담당자가 손인은에서 변경되었습니다")] == ["손인은"]


# ── 리뷰(팀장, PR #571)에서 찾은 대량 미탐 — 조사 목록·라벨 필터 보강(#484 후속) ──
# 첫 구현이 core 테스트는 통과했지만, main 대비 21만 건 차등 비교에서 이름 탐지가
# 통째로 사라진 경우가 1,064건이었다. 두 가지 원인이 있었다.


@pytest.mark.parametrize(
    "text, name",
    [
        ("담당자 김민수한테 연락해 주세요", "김민수"),  # 한테
        ("고객 김민수랑 통화했습니다", "김민수"),  # 랑
        ("대표 박서준께 전달드렸습니다", "박서준"),  # 께
        ("담당자 이도현하고 회의", "이도현"),  # 하고
        ("팀장 최유진처럼 처리", "최유진"),  # 처럼
        ("신청인 정수빈부터 순서대로", "정수빈"),  # 부터
    ],
)
def test_previously_missing_particles_after_a_name_are_recognized(text, name):
    # suffix가 없을 때 "이름 뒤가 낱말 끝이어야 한다"는 조건(#484)이 실제 한국어 조사를
    # 너무 좁게(단일 글자·"에게"·"에서"만) 받아, 훨씬 흔한 조사 뒤의 정상 이름을 대거
    # 놓쳤다. 조사 목록을 넓혀 해결한다.
    assert name in [d.text for d in detect(text)]


@pytest.mark.parametrize(
    "text, name",
    [
        ("명의자 공식", "공식"),  # 좁은 양식 라벨(_FORM_LABELS) 뒤 — 공백만 있어도 강한 단서
        ("예금주: 정밀", "정밀"),  # 좁은 양식 라벨 + 콜론
        ("담당자: 문맥 |", "문맥"),  # 범용 역할어라도 콜론·세로줄이 있으면 강한 단서
    ],
)
def test_common_word_stopwords_are_exempt_after_a_strong_label(text, name):
    # #484가 추가한 정지어(_COMMON_WORDS: 정밀·문맥·전혀·공식)가, 라벨이 이름 자리를
    # 강하게 알려주는 상황에서도 적용돼 실명을 지웠다. 라벨 자체가 좁은 양식 라벨이거나
    # 구분자가 명시적(콜론·세로줄)이면 정지어 필터를 면제해야 한다.
    assert name in [d.text for d in detect(text)]


def test_common_prefix_role_words_without_a_colon_still_drop_stopwords():
    # 대조군(#446 회귀) — "담당자"·"고객"처럼 아주 흔한 역할어는 공백만 있으면(콜론 없이)
    # 여전히 약한 단서로 남는다. 안 그러면 "담당자 최근 변경"의 "최근"이 다시 이름으로
    # 오탐된다 — 위 "담당자: 문맥"과 구분자(콜론 유무)만 다르다.
    assert detect("담당자 최근 변경") == []
    assert detect("고객 문의 접수") == []


@pytest.mark.parametrize(
    "text, name",
    [
        ("담당자 김가을님 확인", "김가"),
        ("고객 김가을이 방문", "김가"),
    ],
)
def test_name_ending_in_a_particle_looking_syllable_is_still_masked_up_to_main(text, name):
    # 리뷰(팀장, PR #571) — "을"이 _NAME_TAIL_STOP이라 "김가을"의 "을"이 이름에서 잘리고
    # "김가"만 남는데, 뒤에 남은 "을님"(조사+존칭)·"을이"(조사 두 개)가 종결어미 목록의
    # 어떤 옵션과도 안 맞아 통째로 놓쳤다. main도 "김가"까지만 가려 완전하지는 않았지만,
    # 적어도 그만큼은 가리도록 조사를 1~2개 반복하고 뒤에 존칭이 더 붙어도 받는다.
    assert name in [d.text for d in detect(text)]


# ── 역할어 "상담원"(#580) ───────────────────────────────────────────
# "상담사"는 직함 단서였지만 같은 뜻의 "상담원"은 없어서, 고객센터 상담 기록처럼 존칭 없이
# "담당 상담원 김민수"로 쓰면 이름을 통째로 놓쳤다.


@pytest.mark.parametrize(
    "text, name",
    [
        ("담당 상담원 김민수", "김민수"),
        ("상담원 박서준에게 감사 인사를 남김", "박서준"),
        ("[상담 1] 전화 상담 · 담당 상담원 강태오", "강태오"),
        ("김민수 상담원이 안내했습니다", "김민수"),
    ],
)
def test_counselor_role_word_is_a_name_cue(text, name):
    assert name in [d.text for d in detect(text)]


@pytest.mark.parametrize(
    "text", ["상담원 연결 대기 중입니다", "상담원 연결해 드릴게요", "상담원 배정은 내일"]
)
def test_counselor_followed_by_a_common_word_is_not_a_name(text):
    # "상담사"와 같은 직함 규칙을 따른다 — 직함만 단서일 땐 성+2자 풀네임만 받고, 흔한 낱말은 거른다.
    assert detect(text) == []
