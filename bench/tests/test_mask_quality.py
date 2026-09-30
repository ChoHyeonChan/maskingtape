# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""mask_quality.py의 유출(leak) 판정과 구조 보존(길이) 검증 로직을 확인한다."""

from __future__ import annotations

import random
import re
from collections.abc import Sequence

from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer, PseudonymAnonymizer
from maskingtape.anonymizers.base import Anonymizer
from maskingtape.anonymizers.label import DEFAULT_LABELS
from maskingtape.detectors import (
    AccountDetector,
    BirthDateDetector,
    BusinessRegistrationDetector,
    CreditCardDetector,
    DriverLicenseDetector,
    NameDetector,
    PassportDetector,
    PhoneDetector,
    RRNDetector,
)
from maskingtape.detectors.base import Detector
from maskingtape.detectors.financial.creditcard import _luhn_ok
from maskingtape.detectors.identity.rrn import _checksum_ok
from maskingtape.pipeline import Pipeline
from maskingtape.types import Detection

from bench.evaluators.mask_quality import (
    evaluate_mask_quality,
    format_mask_quality_report,
)
from bench.generator.entities import generate_entity


class _HalfMaskAnonymizer(Anonymizer):
    """테스트 전용 — 탐지된 구간의 앞 절반만 마스킹해 '경계가 어긋난 부분 유출' 상황을 흉내낸다."""

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            half = (d.end - d.start) // 2
            masked = "*" * half + text[d.start + half : d.end]
            text = text[: d.start] + masked + text[d.end :]
        return text


class _NarrowerThanGoldDetector(Detector):
    """테스트 전용 — 정답 구간보다 좁게 탐지해 "탐지가 정답보다 좁을 때" 상황을 흉내낸다(#498).

    실제 core NameDetector가 "고객 홍길동양 님"에서 존칭 "양"을 포함한 이름 뒤 글자까지
    탐지하지 못하는 것과 같은 상황이다 — 감사에서 실측 재현한 케이스를 그대로 옮겼다.
    """

    kind = "name"

    def __init__(self, narrow_start: int, narrow_end: int):
        self.narrow_start = narrow_start
        self.narrow_end = narrow_end

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind=self.kind,
                start=self.narrow_start,
                end=self.narrow_end,
                text=text[self.narrow_start : self.narrow_end],
                confidence=1.0,
                detector="_NarrowerThanGoldDetector",
            )
        ]


class _OverExposedAnonymizer(Anonymizer):
    """테스트 전용 — 앞 5글자를 남겨 keep_head=2로 '선언'한 것보다 더 많이 새는 버그를 흉내낸다."""

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            keep = min(5, d.end - d.start)
            masked = text[d.start : d.start + keep] + "*" * (d.end - d.start - keep)
            text = text[: d.start] + masked + text[d.end :]
        return text


def test_no_leak_when_pii_is_correctly_masked():
    """core가 실제로 탐지·마스킹하는 phone은 원문이 결과에 남으면 안 된다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline())
    assert result.leak_count == 0
    assert result.full_leak_count == 0
    assert result.partial_leak_count == 0
    assert result.gold_pii_count == 1


def test_leak_detected_when_kind_has_no_detector_yet():
    """core에 탐지기가 없는 종류는 마스킹이 전혀 안 되므로 완전 유출로 잡혀야 한다.

    core는 gold label의 kind 문자열이 아니라 텍스트 내용만 보고 탐지하므로, kind 이름만
    바꿔서는 "탐지기가 없다"는 상황을 흉내낼 수 없다 (core에 이름 탐지기가 생기면 어떤
    kind로 라벨링하든 "김민준"은 실제로 탐지·마스킹된다). 그래서 detectors=[]인 파이프라인을
    직접 만들어 core의 현재 탐지기 구성과 완전히 무관하게 "탐지기가 없는 경우" 자체를 재현한다.
    """
    rows = [{"text": "김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}]}]
    result = evaluate_mask_quality(rows, Pipeline(detectors=[]))
    assert result.leak_count == 1
    assert result.full_leak_count == 1
    assert result.partial_leak_count == 0
    assert result.leaks[0].kind == "name"
    assert result.leaks[0].value == "김민준"
    assert result.leaks[0].exposed_ratio == 1.0
    assert not result.leaks[0].is_partial


def test_partial_leak_when_boundary_masking_is_incomplete():
    """탐지는 됐지만 구간의 일부만 가려지면(경계 오류) 부분 유출로 구분돼야 한다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=_HalfMaskAnonymizer()))
    assert result.leak_count == 1
    assert result.full_leak_count == 0
    assert result.partial_leak_count == 1
    assert 0 < result.leaks[0].exposed_ratio < 1.0
    assert result.leaks[0].is_partial


def test_leak_rate_is_zero_when_no_gold_pii():
    result = evaluate_mask_quality([{"text": "회의는 내일입니다.", "labels": []}], Pipeline())
    assert result.leak_rate == 0.0
    assert result.gold_pii_count == 0


def test_length_preserved_rate_full_when_all_lengths_match():
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline())
    assert result.length_mismatch_count == 0
    assert result.length_preserved_rate == 1.0


def test_format_mask_quality_report_is_readable():
    rows = [
        {"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]},
        {"text": "김민준님 안녕하세요.", "labels": [{"kind": "name", "start": 0, "end": 3}]},
    ]
    result = evaluate_mask_quality(rows, Pipeline(detectors=[]))
    report = format_mask_quality_report(result)
    assert "유출" in report
    assert "name" in report


def test_no_leak_with_label_strategy():
    """label 전략([전화번호] 치환)도 mask와 똑같이 원문이 안 남아야 한다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=LabelAnonymizer()), strategy="label")
    assert result.leak_count == 0
    assert result.length_mismatch_count == 1  # "[전화번호]"는 원문과 길이가 다름 — 정상


def test_no_leak_with_pseudonym_strategy():
    """pseudonym 전략(그럴듯한 가짜 값 치환)도 원문이 안 남아야 한다."""
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=PseudonymAnonymizer(seed=1)), strategy="pseudonym")
    assert result.leak_count == 0


def test_label_and_pseudonym_merge_overlapping_detections_before_substituting_directly():
    """core#494(PR #517)가 고친 속성을 bench가 독립적으로 재검증한다 — core 자체 단위테스트와
    별개로, 실제 detector 출력과 bench가 평소에 쓰는 호출 경로로도 안전한지 확인한다.

    치환형 전략(label/pseudonym)은 구간을 뒤에서부터 다른 길이의 문자열로 바꾸는데, 겹친
    탐지를 Pipeline 없이 anonymizer.apply()에 그대로 넘기면 먼저 바뀐 안쪽 구간 때문에 위치가
    밀려 바깥 구간의 꼬리가 원문 그대로 남을 수 있었다("연락처 010-1234-5678 끝"에서 바깥
    전화번호와 안쪽 마지막 세 글자가 겹치면 "[전화번호]678 끝"처럼 새는 식). 지금은 apply()
    자체가 resolve_overlaps로 먼저 합친 뒤 바꾸므로, Pipeline을 거치지 않고 직접 호출해도
    안전해야 한다."""
    text = "연락처 010-1234-5678 끝"
    outer = PhoneDetector().detect(text)[0]
    assert outer.text == "010-1234-5678"
    # 바깥 탐지의 마지막 세 글자와 겹치는 가짜 탐지를 끼워 넣는다 — 다른 kind, 더 낮은 confidence.
    inner = Detection(
        kind="account",
        start=outer.end - 3,
        end=outer.end,
        text=text[outer.end - 3 : outer.end],
        confidence=0.6,
        detector="fake",
    )
    detections = [outer, inner]

    for anonymizer in (LabelAnonymizer(), PseudonymAnonymizer(seed=1)):
        result = anonymizer.apply(text, detections)
        assert "678" not in result, (
            f"{type(anonymizer).__name__}: 겹친 탐지를 Pipeline 없이 직접 넘겼을 때 "
            f"전화번호 뒷자리가 원문 그대로 샘: {result!r}"
        )
        assert "끝" in result, f"{type(anonymizer).__name__}: 겹침 병합이 탐지 밖 텍스트까지 건드림: {result!r}"


def test_label_strategy_catches_partial_leak_when_detection_is_narrower_than_gold():
    """#498 — 예전엔 label/pseudonym이 "원문 값 전체가 결과에 통째로 남아있는지"만 봐서,
    탐지가 정답보다 좁을 때(예: "홍길동양"이 정답인데 "홍길동"까지만 탐지) 뒤의 "양"이 원문
    그대로 새는데도 유출 0건으로 오판했다("고객 [이름]양 님"). 탐지 구간이 정답 구간을
    얼마나 덮었는지(_coverage_gap_ratio)로 보게 고친 뒤에는 이 부분 유출이 잡혀야 한다."""
    text = "고객 홍길동양 님 안녕하세요."
    gold_start, gold_end = text.index("홍길동양"), text.index("홍길동양") + len("홍길동양")
    narrow_end = gold_start + len("홍길동")  # "양"만 탐지 밖에 남김
    rows = [{"text": text, "labels": [{"kind": "name", "start": gold_start, "end": gold_end}]}]

    detector = _NarrowerThanGoldDetector(gold_start, narrow_end)
    for strategy, anonymizer in (("label", LabelAnonymizer()), ("pseudonym", PseudonymAnonymizer(seed=1))):
        pipeline = Pipeline(detectors=[detector], anonymizer=anonymizer)
        result = evaluate_mask_quality(rows, pipeline, strategy=strategy)
        assert result.leak_count == 1, f"{strategy}: 탐지 밖에 남은 '양'이 유출로 안 잡힘"
        assert result.partial_leak_count == 1, f"{strategy}: 완전 유출이 아니라 부분 유출이어야 함"
        leak = result.leaks[0]
        assert 0 < leak.exposed_ratio < 1.0
        # 정답 4글자 중 탐지 밖(1글자, "양")만 새므로 노출 비율은 1/4.
        assert leak.exposed_ratio == 0.25, f"{strategy}: 노출 비율 계산이 틀림: {leak.exposed_ratio}"


def test_label_strategy_reports_full_leak_when_nothing_overlaps_gold_span():
    """탐지가 정답 구간과 아예 안 겹치면(#498 이전에도 이미 맞던 경우) 여전히 완전 유출 1.0이어야
    한다 — 커버리지 기반 계산으로 바꾼 뒤에도 "탐지 전혀 없음" 케이스의 기존 동작이 유지되는지
    확인하는 회귀 방지 테스트."""
    rows = [{"text": "고객 홍길동 님 안녕하세요.", "labels": [{"kind": "name", "start": 3, "end": 6}]}]
    result = evaluate_mask_quality(rows, Pipeline(detectors=[]), strategy="label")
    assert result.leak_count == 1
    assert result.full_leak_count == 1
    assert result.leaks[0].exposed_ratio == 1.0


def test_format_mask_quality_report_shows_strategy_and_adjusts_length_note():
    rows = [{"text": "010-1234-5678로 연락주세요.", "labels": [{"kind": "phone", "start": 0, "end": 13}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=LabelAnonymizer()), strategy="label")
    report = format_mask_quality_report(result)
    assert "label" in report
    assert "버그 의심" not in report  # label은 길이가 달라지는 게 정상이므로 버그 신호로 오해하면 안 됨


def test_pseudonym_generated_rrn_never_passes_real_checksum():
    """pseudonym.py의 보안 설계 — 가짜 주민번호가 실제 체크섬을 통과하면 안 된다(회귀 방지)."""
    rng = random.Random(20)
    detector = RRNDetector()
    for seed in range(30):
        entity = generate_entity("rrn", rng, difficulty="easy")
        detections = detector.detect(entity.text)
        assert len(detections) == 1
        fake_text = PseudonymAnonymizer(seed=seed).apply(entity.text, detections)
        digits = "".join(c for c in fake_text if c.isdigit())
        assert len(digits) == 13
        assert not _checksum_ok(digits), f"가짜 주민번호가 진짜 체크섬을 통과함: {fake_text!r}"


def test_numbered_label_gives_same_number_to_identical_repeated_value():
    """#164: label(numbered=True)는 표기가 완전히 같은 반복 값에 같은 번호를 매겨야 한다."""
    text = "자택 번호는 010-1234-5678이고, 직장 번호는 010-1234-5678 입니다."
    detections = PhoneDetector().detect(text)
    assert len(detections) == 2
    result = LabelAnonymizer(numbered=True).apply(text, detections)
    assert result == "자택 번호는 [전화번호1]이고, 직장 번호는 [전화번호1] 입니다."


def test_numbered_label_splits_identical_real_value_with_different_formatting():
    """#164: 알려진 한계 — 같은 실제 번호라도 표기(하이픈 유무 등)가 다르면 다른 번호로 잘못
    분리된다. label.py docstring은 "같은 값은 같은 번호를 받아 동일 인물/번호라는 정보가
    유지된다"고 약속하지만, 비교 기준이 Detection.text(탐지된 원문 그대로)라 표기 차이를
    구분 못 한다. core가 표기 정규화 후 비교하도록 고치면 이 테스트가 깨져서 알 수 있다 —
    그때 이 테스트를 갱신하면 된다(지금은 현재 동작을 고정해두는 회귀 테스트).
    """
    text = "자택 번호는 010-1234-5678이고, 직장 번호는 01012345678 입니다."
    detections = PhoneDetector().detect(text)
    assert len(detections) == 2
    result = LabelAnonymizer(numbered=True).apply(text, detections)
    assert result == "자택 번호는 [전화번호1]이고, 직장 번호는 [전화번호2] 입니다."


def test_pseudonym_generated_card_never_passes_real_luhn():
    """pseudonym.py의 보안 설계 — 가짜 카드번호가 실제 Luhn 체크섬을 통과하면 안 된다(회귀 방지)."""
    rng = random.Random(21)
    detector = CreditCardDetector()
    for seed in range(30):
        entity = generate_entity("card", rng, difficulty="easy")
        detections = detector.detect(entity.text)
        assert len(detections) == 1
        fake_text = PseudonymAnonymizer(seed=seed).apply(entity.text, detections)
        digits = "".join(c for c in fake_text if c.isdigit())
        assert len(digits) == 16
        assert not _luhn_ok(digits), f"가짜 카드번호가 진짜 Luhn을 통과함: {fake_text!r}"
_FAKE_PHONE_RE = re.compile(r"010-\d{4}-\d{4}")


def test_pseudonym_gives_same_fake_value_to_identical_repeated_value():
    """#166: pseudonym은 표기가 완전히 같은 반복 값에 같은 가명을 배정해야 한다(문맥 일관성)."""
    text = "자택 번호는 010-1234-5678이고, 직장 번호는 010-1234-5678 입니다."
    detections = PhoneDetector().detect(text)
    assert len(detections) == 2
    result = PseudonymAnonymizer(seed=1).apply(text, detections)
    fake_phones = _FAKE_PHONE_RE.findall(result)
    assert len(fake_phones) == 2
    assert fake_phones[0] == fake_phones[1]


def test_pseudonym_falls_back_to_label_for_kinds_without_a_fake_value_generator():
    """#230: pseudonym.py의 `_GENERATORS`는 name/phone/email/rrn/card/address 6종만 두고,
    나머지는 docstring에 명시된 대로 `[라벨]` 형태로 폴백한다. core에 나중에 추가된 이 kind들에
    대해 이 폴백 경로가 지금까지 회귀 테스트로 한 번도 고정된 적이 없었다 — 원본이 새지 않는지,
    라벨 형식이 맞는지 직접 확인한다. biz_reg/passport/account 3종은 여기서, birth_date/
    driver_license 2종은 각각 `test_birth_date_label_fallback_uses_korean_label`/
    `test_driver_license_label_fallback_uses_korean_label`에서 검증한다(DEFAULT_LABELS 등록
    누락이라는 별도 회귀가 각각 core#282/core#311로 있었던 kind라 전용 테스트로 분리했다)."""
    rng = random.Random(50)
    cases = [
        ("biz_reg", BusinessRegistrationDetector(), "사업자등록번호는 {}입니다."),
        ("passport", PassportDetector(), "참고용 값: {} 입니다."),
        # account는 문맥어(계좌 등)가 앞뒤 15자 안에 없으면 core가 아예 탐지하지 않는
        # 하드 게이트라(#180), 다른 kind와 달리 문맥어를 반드시 포함해야 한다.
        ("account", AccountDetector(), "계좌번호는 {}입니다."),
    ]
    for kind, detector, template in cases:
        entity = generate_entity(kind, rng, difficulty="easy")
        text = template.format(entity.text)
        detections = detector.detect(text)
        assert len(detections) == 1, f"{kind} 탐지 실패: {text!r}"
        result = PseudonymAnonymizer(seed=1).apply(text, detections)
        assert entity.text not in result, f"{kind} 원본이 그대로 남음: {result!r}"
        assert f"[{DEFAULT_LABELS[kind]}]" in result, f"{kind} 라벨 폴백 형식이 아님: {result!r}"


def test_birth_date_label_fallback_uses_korean_label():
    """#282 (core 해결됨) — #230과 같은 라벨 폴백 경로. birth_date는 pseudonym 생성기가
    없어 라벨로 폴백하는데, `DEFAULT_LABELS`에 등록이 빠져 있어 `[생년월일]`이 아니라
    `[birth_date]`(kind 원문)로 노출됐다. core가 라벨을 채워 고쳤고, 이 테스트는 이제
    고쳐진 동작을 고정한다 — 원본이 새지 않는지, 한글 라벨 형식이 맞는지 확인한다."""
    entity = generate_entity("birth_date", random.Random(51), difficulty="easy")
    text = f"생년월일은 {entity.text}입니다."
    detections = BirthDateDetector().detect(text)
    assert len(detections) == 1

    label_result = LabelAnonymizer().apply(text, detections)
    pseudonym_result = PseudonymAnonymizer(seed=1).apply(text, detections)
    for name, result in (("label", label_result), ("pseudonym", pseudonym_result)):
        assert entity.text not in result, f"{name} 전략에서 원본이 그대로 남음: {result!r}"
        assert f"[{DEFAULT_LABELS['birth_date']}]" in result, (
            f"{name} 전략이 한글 라벨로 폴백하지 않음: {result!r}"
        )
        assert "[birth_date]" not in result, (
            f"{name}: kind 원문이 그대로 노출됨 — core#282가 되돌아갔는지 확인: {result!r}"
        )


def test_driver_license_label_fallback_uses_korean_label():
    """#230과 같은 라벨 폴백 경로 — birth_date(#282)가 core#311로 고쳐진 뒤에도, 그 뒤에 core가
    추가한 driver_license(#267/#305)는 이 회귀 테스트로 한 번도 고정된 적이 없었다. pseudonym
    생성기가 없어 라벨로 폴백하는데, `DEFAULT_LABELS`에 `driver_license` 등록이 없으면 birth_date
    가 겪었던 것과 똑같이 `[운전면허]` 대신 `[driver_license]`(kind 원문)가 그대로 노출된다 —
    이미 core#311이 고쳤지만(main에 머지됨), 재발 방지를 위해 직접 고정해둔다."""
    entity = generate_entity("driver_license", random.Random(56), difficulty="easy")
    text = f"운전면허번호는 {entity.text}입니다."
    detections = DriverLicenseDetector().detect(text)
    assert len(detections) == 1

    label_result = LabelAnonymizer().apply(text, detections)
    pseudonym_result = PseudonymAnonymizer(seed=1).apply(text, detections)
    for name, result in (("label", label_result), ("pseudonym", pseudonym_result)):
        assert entity.text not in result, f"{name} 전략에서 원본이 그대로 남음: {result!r}"
        assert f"[{DEFAULT_LABELS['driver_license']}]" in result, (
            f"{name} 전략이 한글 라벨로 폴백하지 않음: {result!r}"
        )
        assert "[driver_license]" not in result, (
            f"{name}: kind 원문이 그대로 노출됨 — core#311이 되돌아갔는지 확인: {result!r}"
        )


def test_pseudonym_splits_identical_real_value_with_different_formatting():
    """#166: 알려진 한계 — label.py의 #164와 동일한 근본 원인. pseudonym도 (kind, Detection.text)
    로 "같은 개체"를 판별해서, 같은 실제 번호라도 표기(하이픈 유무 등)가 다르면 서로 다른
    가명 두 개를 받는다 — docstring이 약속하는 "그 사람이라는 문맥이 유지된다"가 깨진다.
    core가 표기 정규화 후 비교하도록 고치면 이 테스트가 깨져서 알 수 있다(현재 동작 고정용).
    """
    text = "자택 번호는 010-1234-5678이고, 직장 번호는 01012345678 입니다."
    detections = PhoneDetector().detect(text)
    assert len(detections) == 2
    result = PseudonymAnonymizer(seed=1).apply(text, detections)
    fake_phones = _FAKE_PHONE_RE.findall(result)
    assert len(fake_phones) == 2
    assert fake_phones[0] != fake_phones[1]


def test_keep_head_excludes_intentional_prefix_from_leak():
    """#166: MaskAnonymizer(keep_head=N)로 앞 N글자를 의도적으로 남겼으면, keep_head를
    맞춰서 넘겼을 때 그 부분은 유출로 잡히면 안 된다(직접 재현해 발견한 문제 — 안 맞추면
    설계대로 동작한 마스킹도 '부분 유출'로 오판됐다)."""
    rows = [{"text": "주민번호 800101-1234560 입니다.", "labels": [{"kind": "rrn", "start": 5, "end": 19}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=MaskAnonymizer(keep_head=2)), keep_head=2)
    assert result.leak_count == 0
    assert result.full_leak_count == 0
    assert result.partial_leak_count == 0


def test_keep_head_without_matching_param_still_shows_old_misjudgment():
    """keep_head를 쓰는 걸 evaluate_mask_quality에 안 알려주면(기본 0) 의도된 노출이
    부분 유출로 오판된다는 걸 회귀 고정한다 — #166 발견 당시 실측 그대로(14% 노출)."""
    rows = [{"text": "주민번호 800101-1234560 입니다.", "labels": [{"kind": "rrn", "start": 5, "end": 19}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=MaskAnonymizer(keep_head=2)))  # keep_head 인자 생략
    assert result.leak_count == 1
    assert result.partial_leak_count == 1


def test_keep_head_still_catches_leak_beyond_declared_prefix():
    """keep_head=2라고 '선언'했는데 실제로는 더 많이 새는 버그가 있으면(_OverExposedAnonymizer,
    앞 5글자 노출) 여전히 부분 유출로 잡혀야 한다 — keep_head 지원이 진짜 버그까지 숨기면 안 된다."""
    rows = [{"text": "주민번호 800101-1234560 입니다.", "labels": [{"kind": "rrn", "start": 5, "end": 19}]}]
    result = evaluate_mask_quality(rows, Pipeline(anonymizer=_OverExposedAnonymizer()), keep_head=2)
    assert result.leak_count == 1
    assert result.partial_leak_count == 1
    assert 0 < result.leaks[0].exposed_ratio < 1.0


def test_keep_head_no_longer_fully_exposes_values_shorter_than_it():
    """[core#169 해결됨] MaskAnonymizer(keep_head=N)는 파이프라인 전체에 적용되지만, 이제 실제
    보존은 구간 길이의 절반을 넘지 않아(min(keep_head, span_len//2)) 짧은 값이 통째로 노출되지
    않는다. RRN(14자)용으로 keep_head=2를 줘도 2글자 이름은 최대 1글자만 보존된다. (원래 이
    테스트는 core가 고치기 전의 완전 노출을 잡아두던 canary였고, core #169 수정으로 갱신했다.)
    """
    text = "고객 김민 님 안녕하세요."
    detections = NameDetector().detect(text)
    assert len(detections) == 1
    assert detections[0].text == "김민"
    result = MaskAnonymizer(keep_head=2).apply(text, detections)
    assert result == "고객 김* 님 안녕하세요."  # 절반 상한 → 최대 1글자 보존, 통째 노출 안 됨
    assert "김민" not in result
