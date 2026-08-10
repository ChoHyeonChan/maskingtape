"""Pipeline._resolve_overlaps()의 겹침 병합 계약을 확인한다.

핵심 계약(pipeline.py docstring에 명시된 실제 유출 사고 기반): 겹치는 탐지 구간은 절대
통째로 버리지 않는다. 예전엔 주소 탐지기가 주민등록번호 앞자리를 번지로 삼켜 구간이
겹쳤을 때, 겹친 탐지를 통째로 버려서 confidence 1.0짜리 주민번호 탐지가 통보조차 안 되고
사라진 채 마스킹도 안 된 뒷자리가 그대로 노출된 사고가 있었다(#171). 지금은 겹치면
합집합으로 병합하고 confidence가 높은 쪽의 kind를 따르도록 고쳐져 있는데, 이 계약을
지키는 자동 테스트가 core에도 bench에도 없어서 회귀해도 아무도 못 잡는 사각지대였다.

`_resolve_overlaps`는 private 함수지만, bench가 core의 다른 private 검증 함수(`_luhn_ok`,
`_checksum_ok`)도 이미 직접 테스트하는 것과 같은 패턴이다.
"""

from __future__ import annotations

from maskingtape.detectors.base import Detector
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection


class _FixedSpanDetector(Detector):
    """테스트 전용 — 항상 고정된 구간 하나를 정해진 confidence로 반환하는 가짜 탐지기."""

    def __init__(self, kind: str, start: int, end: int, confidence: float) -> None:
        self.kind = kind
        self._start = start
        self._end = end
        self._confidence = confidence

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind=self.kind,
                start=self._start,
                end=self._end,
                text=text[self._start : self._end],
                confidence=self._confidence,
                detector="fake",
            )
        ]


_TEXT = "서울특별시 강남구 역삼동 800101-1234560 님께 안내드립니다."


def test_overlapping_detections_merge_into_single_union_span():
    """겹치는 두 탐지는 합집합 구간 하나로 병합돼야 한다 — 둘 다 살아남되 하나로 합쳐진다."""
    pipeline = Pipeline(
        detectors=[
            _FixedSpanDetector("address", 0, 13, confidence=0.8),
            _FixedSpanDetector("rrn", 10, 24, confidence=1.0),
        ]
    )
    result = pipeline.scan(_TEXT)
    assert len(result) == 1
    merged = result[0]
    assert merged.start == 0
    assert merged.end == 24


def test_overlap_kind_follows_higher_confidence_detector():
    """병합된 구간의 kind는 confidence가 더 높은 탐지기를 따라야 한다."""
    pipeline = Pipeline(
        detectors=[
            _FixedSpanDetector("address", 0, 13, confidence=0.8),
            _FixedSpanDetector("rrn", 10, 24, confidence=1.0),
        ]
    )
    result = pipeline.scan(_TEXT)
    assert result[0].kind == "rrn"


def test_overlap_never_silently_drops_the_higher_confidence_detection():
    """#171의 핵심 — 과거엔 겹치면 통째로 버려서 confidence 1.0짜리 RRN이 scan() 결과에서
    아예 사라졌다(호출자는 주민번호가 없다고 통보받음). 지금은 병합만 되고 절대 통보 자체가
    사라지면 안 된다 — 어느 순서로 detector를 등록해도 결과가 0건이 되면 안 된다."""
    forward = Pipeline(
        detectors=[
            _FixedSpanDetector("address", 0, 13, confidence=0.8),
            _FixedSpanDetector("rrn", 10, 24, confidence=1.0),
        ]
    ).scan(_TEXT)
    backward = Pipeline(
        detectors=[
            _FixedSpanDetector("rrn", 10, 24, confidence=1.0),
            _FixedSpanDetector("address", 0, 13, confidence=0.8),
        ]
    ).scan(_TEXT)
    assert len(forward) == 1
    assert len(backward) == 1
    assert forward[0].kind == backward[0].kind == "rrn"


def test_non_overlapping_detections_both_kept_separately():
    """겹치지 않는 탐지는 병합되지 않고 둘 다 그대로 유지돼야 한다(기본 케이스 회귀 방지)."""
    pipeline = Pipeline(
        detectors=[
            _FixedSpanDetector("name", 0, 3, confidence=0.75),
            _FixedSpanDetector("phone", 10, 23, confidence=1.0),
        ]
    )
    result = pipeline.scan("김민준님 연락처는 010-1234-5678 입니다.")
    assert len(result) == 2
    kinds = {d.kind for d in result}
    assert kinds == {"name", "phone"}


def test_fully_contained_overlap_keeps_the_wider_span():
    """한 구간이 다른 구간을 완전히 포함하면, 넓은 쪽 구간이 남는다(더 가리기=안전 — 마스킹
    범위 자체는 문제없다)."""
    pipeline = Pipeline(
        detectors=[
            _FixedSpanDetector("address", 0, 24, confidence=0.9),
            _FixedSpanDetector("rrn", 10, 24, confidence=1.0),
        ]
    )
    result = pipeline.scan(_TEXT)
    assert len(result) == 1
    assert result[0].start == 0
    assert result[0].end == 24


def test_fully_contained_overlap_applies_confidence_based_kind_rule():
    """[core#172 해결됨] 완전 포함(fully-contained) 겹침도 부분 겹침과 동일하게 confidence가
    높은 쪽이 kind를 담당한다. confidence 1.0짜리 rrn이 confidence 0.9짜리 address 안에 완전히
    포함되면, 넓은 구간(0~24)은 그대로 가리되 kind는 **rrn(confidence 1.0)**으로 보고된다 —
    더 민감한 종류를 감추지 않는다. (원래 이 테스트는 core가 고치기 전의 비일관 동작을 잡아두던
    canary였고, core #172 수정으로 새 동작에 맞춰 갱신했다.)
    """
    pipeline = Pipeline(
        detectors=[
            _FixedSpanDetector("address", 0, 24, confidence=0.9),
            _FixedSpanDetector("rrn", 10, 24, confidence=1.0),
        ]
    )
    result = pipeline.scan(_TEXT)
    assert len(result) == 1
    assert result[0].kind == "rrn"  # 확신도 높은 쪽(1.0)이 kind를 담당
    assert result[0].confidence == 1.0
    assert result[0].start == 0 and result[0].end == 24  # 넓은 쪽 구간은 유지(더 가리기=안전)
