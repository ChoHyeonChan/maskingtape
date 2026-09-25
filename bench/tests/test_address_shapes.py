# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""#423이 고친 주소 형태 생성 재료(address_shapes.py)의 무결성 검증(#431).

핵심 계약 셋:
1. 형태마다 core AddressDetector가 입력 전체를 **한 구간으로** 잡는다 — 구간이 끊기면 뒤따르는
   도로명·건물번호가 원문으로 남는 부분 유출이라, 통째로 잡히지 않으면 곧 회귀다.
2. `gen_address(extended=True)`가 8형태를 실제로 만들어 낸다 — 재료만 있고 안 나오면 벤치는 계속 눈이 먼다.
3. 기본 생성(extended=False)은 새 형태를 절대 섞지 않는다 — 섞으면 난수 흐름이 바뀌어 synth_v1.jsonl을
   시드로 다시 만들 수 없다.
"""

from __future__ import annotations

import random

import pytest
from maskingtape.detectors import AddressDetector

from bench.generator.address_shapes import EXTENDED_SHAPES, SHAPE_MARKERS, gen_extended_address
from bench.generator.entities import gen_address


def test_every_shape_has_a_marker_and_a_generator():
    assert set(EXTENDED_SHAPES) == set(SHAPE_MARKERS)
    assert len(EXTENDED_SHAPES) == 8  # core test_address.py의 `# --- #423` 섹션이 고정한 형태 수


@pytest.mark.parametrize("name", list(EXTENDED_SHAPES))
def test_shape_is_detected_whole_by_core(name):
    """형태마다 300번 뽑아 전부 정확히 한 건, 입력 전체 구간으로 잡히는지 확인한다.

    데이터셋 한 벌로는 형태당 몇 건뿐이라(seed 42에서 2~8건) 이 반복 검증이 형태별 근거다.
    """
    rng = random.Random(431)
    detector = AddressDetector()
    for _ in range(300):
        text = EXTENDED_SHAPES[name](rng)
        found = detector.detect(text)
        assert [d.text for d in found] == [text], f"{name}: {text!r} 부분 유출 또는 미탐 -> {found!r}"


@pytest.mark.parametrize("name", list(EXTENDED_SHAPES))
def test_shape_output_matches_only_its_own_marker_family(name):
    """마커가 자기 형태의 출력을 알아본다 — 커버리지·v1 면역 테스트가 이 마커에 기댄다."""
    rng = random.Random(432)
    for _ in range(300):
        assert SHAPE_MARKERS[name].search(EXTENDED_SHAPES[name](rng)), name


def test_extended_generation_produces_all_shapes():
    rng = random.Random(433)
    texts = [gen_extended_address(rng) for _ in range(2000)]
    for name, marker in SHAPE_MARKERS.items():
        assert any(marker.search(t) for t in texts), f"{name} 형태가 2000건에서 한 번도 안 나옴"


def test_gen_address_extended_mixes_shapes_and_default_never_does():
    rng = random.Random(434)
    extended = [gen_address(rng, "mixed", extended=True).text for _ in range(2000)]
    assert any(m.search(t) for t in extended for m in SHAPE_MARKERS.values())

    # 기본(v1) 경로는 새 형태를 한 건도 섞지 않는다 — 섞으면 synth_v1.jsonl 재생성이 깨진다.
    rng = random.Random(435)
    for difficulty in ("easy", "hard", "mixed"):
        for _ in range(1500):
            text = gen_address(rng, difficulty).text
            assert not any(m.search(text) for m in SHAPE_MARKERS.values()), f"v1 경로에 새 형태 유입: {text!r}"

