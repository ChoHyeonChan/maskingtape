"""라벨 치환 전략 테스트 — 합성 데이터만 사용한다."""

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer
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
