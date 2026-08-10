"""파이프라인 통합 테스트 — 합성 데이터만 사용한다."""

from maskingtape import Pipeline

SYNTHETIC = "고객 주민번호 800101-1234560 확인 부탁드립니다"


def test_anonymize_masks_rrn():
    result = Pipeline().anonymize(SYNTHETIC)
    assert "800101-1234560" not in result.text
    assert result.text.count("*") == len("800101-1234560")
    assert len(result.detections) == 1


def test_scan_reports_correct_positions():
    d = Pipeline().scan(SYNTHETIC)[0]
    assert SYNTHETIC[d.start : d.end] == d.text


def test_clean_text_untouched():
    clean = "오늘 회의는 오후 3시입니다"
    result = Pipeline().anonymize(clean)
    assert result.text == clean
    assert result.detections == []


def test_multiple_kinds_in_one_text():
    text = "담당자 010-1234-5678 / hong@example.com / 800101-1234560"
    kinds = {d.kind for d in Pipeline().scan(text)}
    assert kinds == {"phone", "email", "rrn"}


def test_detects_address_alongside_other_kinds():
    text = "배송지 서울특별시 강남구 역삼동 123-4 / 연락처 010-1234-5678"
    kinds = {d.kind for d in Pipeline().scan(text)}
    assert kinds == {"address", "phone"}


# --- 보안: 겹치는 탐지를 버리면 개인정보가 마스킹되지 않고 남는다 ---


def test_rrn_right_after_an_address_is_still_masked():
    """주소 뒤에 바로 주민번호가 오는 한국 서식의 흔한 형태.

    번지가 없으면 주소 탐지기가 주민번호 앞 네 자리를 번지로 삼켜 두 구간이 겹쳤고,
    예전 구현은 겹치면 뒤 탐지를 통째로 버려 주민번호 뒷자리가 그대로 노출됐다.
    """
    text = "서울특별시 강남구 역삼동 800101-1234560"
    result = Pipeline().anonymize(text)
    assert "1234560" not in result.text  # 주민번호 뒷자리(가장 민감한 부분)
    assert "800101" not in result.text
    # 주민번호를 찾았다는 사실 자체도 호출자에게 보고돼야 한다
    assert "rrn" in {d.kind for d in result.detections}


def test_phone_right_after_an_address_is_still_masked():
    text = "부산광역시 해운대구 우동 010-9876-5432"
    result = Pipeline().anonymize(text)
    assert "9876" not in result.text
    assert "5432" not in result.text
    assert "phone" in {d.kind for d in result.detections}


def test_overlapping_detections_are_merged_not_dropped():
    """겹치는 구간은 합집합으로 가린다 — 덜 가리는 것보다 더 가리는 쪽이 안전하다."""
    text = "서울특별시 강남구 역삼동 800101-1234560"
    detections = Pipeline().scan(text)
    covered = sum(d.end - d.start for d in detections)
    # 탐지된 구간들이 주소 시작부터 주민번호 끝까지를 빠짐없이 덮어야 한다
    assert covered >= len("서울특별시 강남구 역삼동") + len("800101-1234560")
    assert all(text[d.start : d.end] == d.text for d in detections)


def test_fully_contained_overlap_reports_the_higher_confidence_kind():
    """[#172] 완전 포함 겹침도 부분 겹침처럼 확신도 높은 쪽이 kind를 담당한다.

    넓은 address(0.9) 안에 rrn(1.0)이 완전히 포함되면, 넓은 구간을 그대로 가리되
    더 민감한 rrn을 감추지 않고 kind='rrn'으로 보고한다.
    """
    from maskingtape.detectors.base import Detector
    from maskingtape.types import Detection

    class _Fixed(Detector):
        def __init__(self, kind: str, start: int, end: int, confidence: float) -> None:
            self.kind = kind
            self._start, self._end, self._conf = start, end, confidence

        def detect(self, text: str) -> list[Detection]:
            return [
                Detection(
                    kind=self.kind,
                    start=self._start,
                    end=self._end,
                    text=text[self._start : self._end],
                    confidence=self._conf,
                    detector="Fixed",
                )
            ]

    text = "서울특별시 강남구 역삼동 800101-1234560"
    result = Pipeline(detectors=[_Fixed("address", 0, 24, 0.9), _Fixed("rrn", 10, 24, 1.0)]).scan(text)
    assert len(result) == 1
    assert result[0].kind == "rrn"  # 더 민감한 종류를 감추지 않는다
    assert result[0].confidence == 1.0
    assert (result[0].start, result[0].end) == (0, 24)  # 넓은 쪽 구간은 그대로(더 가리기=안전)
