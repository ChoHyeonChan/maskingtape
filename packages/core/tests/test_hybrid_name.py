"""하이브리드 이름 탐지 테스트 — 합성 데이터만 사용.

규칙으로 후보를 먼저 훑어, 후보가 없는 텍스트는 LLM을 건너뛴다.
LLM 호출 여부는 client 주입으로 관찰한다(CI에는 Ollama가 없다).
"""

from maskingtape.detectors.name import has_name_candidate
from maskingtape.detectors.name_llm import LLMNameDetector


# --- 후보 판정 필터 ---


def test_candidate_true_when_surname_present():
    assert has_name_candidate("그래서 홍길동이 어제 왔어") is True


def test_candidate_true_for_compound_surname():
    # 복성(남궁)은 성씨 사전에 없어도 사전에 새로 넣었으므로 후보로 잡힌다
    assert has_name_candidate("남궁민수가 보고했다") is True


def test_candidate_true_from_title_cue_even_without_known_surname():
    # 성씨 사전에 없는 이름이라도 직함 단서가 있으면 후보 (희귀 성씨 안전망)
    assert has_name_candidate("탁예린 팀장이 참석") is True


def test_candidate_false_for_data_without_korean():
    # 한글 성씨로 시작하는 뭉치가 없는 입력 — 이름이 있을 수 없으므로 LLM을 건너뛴다
    assert has_name_candidate("010-1234-5678") is False
    assert has_name_candidate("order@shop.com 20260723 USD 15000") is False


def test_candidate_ignores_pure_domain_label_word():
    # "이메일"은 도메인 라벨 단어라 '이'가 성씨로 오인되지 않는다
    assert has_name_candidate("이메일") is False
    assert has_name_candidate("주소") is False


def test_candidate_stays_loose_on_common_korean_words():
    # 정직한 한계: '하세요'의 '하', '주문'의 '주'가 성씨라 후보로 걸린다.
    # 형태만으로 이름과 일반어를 못 가르는 건 이름 탐지의 근본 난제 — 그래서 안전하게(느슨하게)
    # LLM으로 넘기고 최종 판단을 맡긴다. 확실히 걸러지는 건 '한글이 없는' 순수 데이터뿐이다.
    assert has_name_candidate("주문번호를 입력하세요") is True


# --- LLM 호출 스킵 ---


def test_skips_llm_when_no_candidate():
    called = False

    def client(_text):
        nonlocal called
        called = True
        return ["김철수"]

    detector = LLMNameDetector(client=client)
    assert detector.detect("010-1234-5678, order@shop.com") == []
    assert called is False  # 후보가 없으니 LLM을 부르지 않았다
    assert detector.calls == 0


def test_calls_llm_when_candidate_present():
    detector = LLMNameDetector(client=lambda _t: ["홍길동"])
    found = detector.detect("그래서 홍길동이 어제 왔어")
    assert [d.text for d in found] == ["홍길동"]
    assert detector.calls == 1


def test_call_count_tracks_only_real_calls():
    detector = LLMNameDetector(client=lambda _t: [])
    detector.detect("010-1234-5678")          # 후보 없음 → 스킵
    detector.detect("고객 김철수님")           # 후보 있음 → 호출
    detector.detect("USD 5000 paid")          # 후보 없음(한글 없음) → 스킵
    assert detector.calls == 1
