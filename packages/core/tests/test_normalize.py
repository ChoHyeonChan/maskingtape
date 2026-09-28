# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""입력 표기 정리(#490) 테스트 — 전부 합성 값.

특수 문자는 소스에 그대로 두지 않고 chr()로 만든다(편집기·도구가 바꿔 버리는 사고 방지).
"""

import time
import tracemalloc
import unicodedata

import pytest

from maskingtape import Pipeline
from maskingtape.anonymizers import MaskAnonymizer
from maskingtape.detectors import Detector
from maskingtape.normalize import normalize
from maskingtape.types import Detection

NBSP, IDEO_SPACE, ZWSP, BOM, SHY = chr(0xA0), chr(0x3000), chr(0x200B), chr(0xFEFF), chr(0xAD)
EN_DASH, MINUS, FW_HYPHEN = chr(0x2013), chr(0x2212), chr(0xFF0D)


def fullwidth(text: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in text)


def nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


# ── normalize() 단위 ─────────────────────────────────────────────────


def test_ascii_is_left_as_is():
    prepared = normalize("800101-1234560")
    assert prepared.text == "800101-1234560"
    assert prepared.starts is None


def test_plain_korean_is_left_as_is():
    text = "고객 김민수님 연락처 010-1234-5678"
    assert normalize(text).text == text


@pytest.mark.parametrize(
    "raw, expected",
    [
        (fullwidth("800101-1234560"), "800101-1234560"),
        ("010" + MINUS + "1234" + EN_DASH + "5678", "010-1234-5678"),
        ("4111" + NBSP + "1111" + IDEO_SPACE + "1111", "4111 1111 1111"),
        ("성명" + fullwidth(":") + " 홍길동", "성명: 홍길동"),
        ("123" + FW_HYPHEN + "45", "123-45"),
        (chr(0x0661) + chr(0x0662), "12"),  # 아랍-인도 숫자도 십진 숫자다
    ],
)
def test_same_length_replacements_keep_positions(raw, expected):
    prepared = normalize(raw)
    assert prepared.text == expected
    assert len(prepared.text) == len(raw)
    assert prepared.starts is None


def test_circled_digit_is_not_turned_into_a_digit():
    # NFKC를 통째로 쓰면 ①이 1이 되어 뒤 번호와 붙는다 — 그러면 오히려 덜 가린다.
    assert normalize(chr(0x2460) + "010-1234-5678").text[0] == chr(0x2460)


def test_invisible_characters_are_removed_and_positions_map_back():
    raw = "800101-" + ZWSP + "1234560"
    prepared = normalize(raw)
    assert prepared.text == "800101-1234560"
    restored = prepared.restore(Detection(kind="rrn", start=0, end=14, text="800101-1234560"))
    assert (restored.start, restored.end) == (0, len(raw))
    assert restored.text == raw


def test_decomposed_hangul_is_composed_and_maps_to_all_jamo():
    raw = "고객 " + nfd("김민수") + "님"
    prepared = normalize(raw)
    assert prepared.text == "고객 김민수님"
    restored = prepared.restore(Detection(kind="name", start=3, end=6, text="김민수"))
    assert raw[restored.start : restored.end] == nfd("김민수")
    assert restored.text == nfd("김민수")


def test_syllable_followed_by_final_jamo_is_composed():
    # 완성형 음절 뒤에 종성 자모만 붙은 표기(가 + ᆼ = 강)도 앞 글자와 묶어 합친다
    raw = "고객 가" + chr(0x11BC) + "민수님, 긴 평범한 문장이 뒤에 이어진다."
    prepared = normalize(raw)
    assert prepared.text == "고객 강민수님, 긴 평범한 문장이 뒤에 이어진다."
    restored = prepared.restore(Detection(kind="name", start=3, end=6, text="강민수"))
    assert raw[restored.start : restored.end] == "가" + chr(0x11BC) + "민수"
    # 특수 문자 뒤의 평범한 구간도 한 글자씩 제자리로 돌아간다
    tail = prepared.text.index("문장")
    restored = prepared.restore(Detection(kind="x", start=tail, end=tail + 2, text="문장"))
    assert restored.text == "문장"


def test_restore_keeps_original_text_even_when_positions_are_the_same():
    raw = fullwidth("010-1234-5678")
    prepared = normalize(raw)
    restored = prepared.restore(Detection(kind="phone", start=0, end=13, text="010-1234-5678"))
    assert (restored.start, restored.end, restored.text) == (0, 13, raw)


# ── Pipeline: 이슈 #490 표의 입력이 전부 가려진다 ────────────────────


def assert_masked(text: str, value: str) -> None:
    start = text.index(value)
    end = start + len(value)
    masked = Pipeline().anonymize(text).text
    assert masked[start:end] == "*" * (end - start), masked


@pytest.mark.parametrize(
    "text, value",
    [
        ("주민번호 " + fullwidth("800101-1234560"), fullwidth("800101-1234560")),
        ("주민번호 800101-" + ZWSP + "1234560", "800101-" + ZWSP + "1234560"),
        ("주민번호 800101" + SHY + "-1234560", "800101" + SHY + "-1234560"),
        ("전화 010" + MINUS + "1234" + MINUS + "5678", "010" + MINUS + "1234" + MINUS + "5678"),
        ("전화 " + fullwidth("010-1234-5678"), fullwidth("010-1234-5678")),
        ("전화 010-1234-" + BOM + "5678", "010-1234-" + BOM + "5678"),
        ("카드 4111" + NBSP + "1111" + NBSP + "1111" + NBSP + "1111",
         "4111" + NBSP + "1111" + NBSP + "1111" + NBSP + "1111"),
        ("카드 4111" + EN_DASH + "1111" + EN_DASH + "1111" + EN_DASH + "1111",
         "4111" + EN_DASH + "1111" + EN_DASH + "1111" + EN_DASH + "1111"),
        ("입금 계좌 110" + EN_DASH + "123" + EN_DASH + "456789", "110" + EN_DASH + "123" + EN_DASH + "456789"),
        ("사업자등록번호 123" + EN_DASH + "45" + EN_DASH + "67891", "123" + EN_DASH + "45" + EN_DASH + "67891"),
        ("사업자등록번호 123" + FW_HYPHEN + "45" + FW_HYPHEN + "67891",
         "123" + FW_HYPHEN + "45" + FW_HYPHEN + "67891"),
        ("운전면허 11" + EN_DASH + "12" + EN_DASH + "345678" + EN_DASH + "90",
         "11" + EN_DASH + "12" + EN_DASH + "345678" + EN_DASH + "90"),
        ("이메일 hong" + ZWSP + "@example.com", "hong" + ZWSP + "@example.com"),
    ],
)
def test_variant_spellings_are_masked(text, value):
    assert_masked(text, value)


def test_decomposed_hangul_name_and_address_are_masked():
    text = nfd("고객 김민수님, 주소 서울특별시 강남구 역삼동 123-4")
    assert_masked(text, nfd("김민수"))
    assert_masked(text, nfd("서울특별시 강남구 역삼동 123-4"))


def test_detections_report_original_text_and_positions():
    text = "주민번호 " + fullwidth("800101-1234560") + ", 전화 010-" + ZWSP + "1234-5678"
    detections = Pipeline().scan(text)
    assert {d.kind for d in detections} == {"rrn", "phone"}
    for d in detections:
        assert text[d.start : d.end] == d.text


# ── 정리 때문에 덜 가리지 않는다 ────────────────────────────────────


@pytest.mark.parametrize(
    "text, value",
    [
        # en-dash가 하이픈으로 바뀌면 계좌 탐지기의 "앞에 하이픈이 붙음" 가드에 걸린다
        ("입금계좌" + EN_DASH + "110-123-456789", "110-123-456789"),
        # 폭 없는 공백을 지우면 뒤 숫자와 붙어 전화번호 경계가 사라진다
        ("전화 010-1234-5678" + ZWSP + "5", "010-1234-5678"),
    ],
)
def test_original_spelling_results_are_kept(text, value):
    assert_masked(text, value)


class _CountingDetector(Detector):
    kind = "name"

    def __init__(self, calls_model: bool) -> None:
        self.calls_model = calls_model
        self.seen: list[str] = []

    def detect(self, text: str) -> list[Detection]:
        self.seen.append(text)
        return []


def test_model_detector_runs_once_on_the_cleaned_text():
    model, rule = _CountingDetector(calls_model=True), _CountingDetector(calls_model=False)
    Pipeline(detectors=[model, rule]).scan("고객 김민수님" + NBSP + "문의")
    assert model.seen == ["고객 김민수님 문의"]
    assert rule.seen == ["고객 김민수님" + NBSP + "문의", "고객 김민수님 문의"]


def test_plain_text_runs_every_detector_once():
    model, rule = _CountingDetector(calls_model=True), _CountingDetector(calls_model=False)
    Pipeline(detectors=[model, rule]).scan("고객 김민수님 문의")
    assert model.seen == rule.seen == ["고객 김민수님 문의"]


def test_model_detector_runs_once_when_only_invisible_characters_are_removed():
    # ❤️의 변형 선택자(U+FE0F)나 폭 없는 공백만 지우면 이름 글자는 그대로다 — 모델은 한 번만
    raw = "고객 김민수님 문의 " + chr(0x2764) + chr(0xFE0F) + ZWSP
    model = _CountingDetector(calls_model=True)
    Pipeline(detectors=[model]).scan(raw)
    assert model.seen == ["고객 김민수님 문의 " + chr(0x2764)]


def test_model_detector_also_sees_the_original_when_letters_change():
    # 자모를 합치면 모델은 정리본에서 원문의 이름 모양을 볼 수 없다 — 원문에서도 한 번 돈다
    raw = nfd("고객 김민수님 문의")
    model = _CountingDetector(calls_model=True)
    Pipeline(detectors=[model]).scan(raw)
    assert model.seen == [raw, "고객 김민수님 문의"]


# ── 검증에서 찾은 빈틈 (#490 독립 검증 1회차) ────────────────────────


def test_invisible_character_between_jamo_does_not_block_composition():
    raw = "고객 " + chr(0x1100) + ZWSP + chr(0x1175) + chr(0x11B7) + nfd("민수") + "님"
    assert normalize(raw).text == "고객 김민수님"
    assert_masked(raw + " 문의", raw[3:-1])


@pytest.mark.parametrize(
    "mark",
    [chr(0x336), chr(0x332), chr(0x301), chr(0x20E3), chr(0xFE0F)],  # 취소선·밑줄·악센트·키캡·변형 선택자
)
def test_marks_on_digits_are_removed(mark):
    value = "".join(c + mark for c in "800101-1234560")
    assert normalize(value).text == "800101-1234560"
    assert_masked("주민번호 " + value, value)


@pytest.mark.parametrize(
    "text, value",
    [
        # SNS에서 공백 대신 쓰는 한글 채움 문자 — 지우면 낱말이 붙으므로 공백으로 본다
        ("주소" + chr(0x3164) + "서울특별시" + chr(0x3164) + "강남구" + chr(0x3164) + "역삼동" + chr(0x3164) + "123-4",
         "서울특별시" + chr(0x3164) + "강남구" + chr(0x3164) + "역삼동" + chr(0x3164) + "123-4"),
        ("고객" + chr(0x3164) + "김민수" + chr(0x3164) + "님 문의", "김민수"),
        # 한글 입력에서 대시로 쓰는 ㅡ
        ("전화 010" + chr(0x3161) + "1234" + chr(0x3161) + "5678", "010" + chr(0x3161) + "1234" + chr(0x3161) + "5678"),
    ],
)
def test_hangul_filler_and_hangul_dash(text, value):
    assert_masked(text, value)


def test_keep_head_counts_only_visible_characters():
    # 보이지 않는 문자가 구간에 끼어도 3글자 이름의 앞 1글자까지만 남긴다(#169의 "최소 절반")
    text = "고객 김민" + ZWSP + "수님 문의"
    masked = Pipeline(anonymizer=MaskAnonymizer(keep_head=2)).anonymize(text).text
    assert masked == "고객 김***님 문의"


def test_keep_head_counts_decomposed_hangul_as_syllables():
    # 자모 8개(김민수)를 8글자로 세면 절반이 4가 되어 이름 두 글자가 드러난다
    text = "고객 " + nfd("김민수") + "님 문의"
    masked = Pipeline(anonymizer=MaskAnonymizer(keep_head=2)).anonymize(text).text
    assert masked == "고객 " + nfd("김") + "*****님 문의"


@pytest.mark.parametrize("keep_head", [2, 3])
def test_keep_head_counts_stray_jamo_with_their_syllable(keep_head):
    # 합쳐지지 않는 중성이 이름 뒤에 붙고 문서 어딘가에 ZWSP가 있으면, 예전 계산은 절반을 부풀려
    # 이름 전체를 드러냈다(#490 독립 검증 2회차). 묶음 단위로 세면 앞 한 글자만 남는다.
    text = "고객 김민수" + chr(0x1175) * 3 + "님 문의" + ZWSP
    masked = Pipeline(anonymizer=MaskAnonymizer(keep_head=keep_head)).anonymize(text).text
    assert masked.startswith("고객 김*")
    assert "민" not in masked and "수" not in masked


def test_keep_head_is_unchanged_for_plain_text():
    masked = Pipeline(anonymizer=MaskAnonymizer(keep_head=2)).anonymize("주민번호 800101-1234560").text
    assert masked == "주민번호 80************"


def _seconds(text: str) -> float:
    start = time.perf_counter()
    normalize(text)
    return time.perf_counter() - start


@pytest.mark.parametrize(
    "unit",
    [
        "a" + (chr(0x301) + chr(0x316)) * 64,  # 결합 문자가 끝없이 이어지는 묶음
        "고객 김민수님 연락처 010-1234-5678입니다. " + chr(0x301),  # 평범한 문서에 결합 문자 하나
    ],
)
def test_normalize_time_grows_linearly(unit):
    small = unit * (40_000 // len(unit))
    large = unit * (160_000 // len(unit))
    _seconds(small)  # 첫 호출의 준비 비용을 뺀다
    # 4배 입력에서 선형이면 약 4배, 이차면 약 16배다
    assert _seconds(large) < 8 * _seconds(small) + 0.05


def test_position_map_memory_stays_small():
    # 대응표를 글자마다 파이썬 정수로 두면 10만 자에 7MB를 넘는다. 특수 문자 하나 섞인 큰 문서로
    # 메모리가 몇 배가 되지 않게, 대응표는 정수 배열(글자당 16바이트)에 담는다
    text = ZWSP + "가" * 100_000
    tracemalloc.start()
    try:
        prepared = normalize(text)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert len(prepared.text) == 100_000
    assert peak < 4_000_000
