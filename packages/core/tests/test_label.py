"""라벨 치환 전략 테스트 — 합성 데이터만 사용한다."""

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer
from maskingtape.anonymizers.label import DEFAULT_LABELS
from maskingtape.detectors import default_detectors
from maskingtape.types import Detection


def test_label_replacement():
    out = Pipeline(anonymizer=LabelAnonymizer()).anonymize("연락처 010-1234-5678")
    assert out.text == "연락처 [전화번호]"


def test_numbered_labels_keep_identity():
    # 같은 값 = 같은 번호, 다른 값 = 다른 번호 → 문맥의 동일성 유지
    text = "A 고객 010-1234-5678, B 고객 010-9876-5432, A 재연락 010-1234-5678"
    out = Pipeline(anonymizer=LabelAnonymizer(numbered=True)).anonymize(text)
    assert out.text == "A 고객 [전화번호1], B 고객 [전화번호2], A 재연락 [전화번호1]"


def test_unknown_kind_falls_back_to_kind_string():
    det = Detection(kind="custom", start=0, end=3, text="abc")
    assert LabelAnonymizer().apply("abc!", [det]) == "[custom]!"


def test_birth_date_has_a_korean_label():
    """#282 — birth_date만 DEFAULT_LABELS에 없어 `[birth_date]`로 노출되던 문제."""
    out = Pipeline(anonymizer=LabelAnonymizer()).anonymize("생년월일은 1990-01-01 입니다")
    assert out.text == "생년월일은 [생년월일] 입니다"


def test_default_labels_cover_every_default_detector_kind():
    """새 탐지기를 추가하면서 라벨을 빠뜨리면 여기서 걸린다.

    이 누락은 지금까지 반복해서 발생했다(#282의 birth_date가 마지막). 라벨이 없으면
    label/pseudonym 결과에 kind 원문(`[birth_date]`)이 그대로 노출된다 — 유출은
    아니지만 사용자에게 보이는 문구라, 사람이 기억하는 대신 테스트가 잡게 한다.
    """
    kinds = {d.kind for d in default_detectors()}
    missing = sorted(kinds - DEFAULT_LABELS.keys())
    assert not missing, f"DEFAULT_LABELS에 빠진 kind: {missing}"
