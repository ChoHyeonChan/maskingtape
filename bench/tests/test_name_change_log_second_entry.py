# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

""""담당자가 A에서 B로 변경되었습니다" 두 번째 이름 미탐(core #589) 회귀 감시.

synth_v1에서 이 템플릿(`bench/generator/documents.py`)이 쓰인 4건을 전수 조사하면
첫 번째 이름(`담당자가` 바로 뒤)은 4/4 탐지되는데 두 번째 이름(`에서 ... 으로` 사이)은
0/4 탐지된다 — 3음절 이름도 똑같이 새는 것으로 보아 기존에 문서화된 "2음절 이름" 한계
(#213/#239)와는 무관한 별개의 원인이다: 이 자리에는 이름을 알아볼 단서 자체가 없다.

동작 원리:
1. `_gen_change_log_doc`이 "담당자가 {이름1}에서 {이름2}로 변경되었습니다" 문서를 만든다.
2. 지금(core #589 고치기 전) 동작을 캐너리로 고정한다 — 이름1은 잡히고 이름2는 안 잡힌다.
3. core #589가 고쳐지면 이름2가 잡히기 시작해 이 캐너리가 깨질 것이다 — 그때
   `assert second_gold in pred`로 뒤집어 정상 회귀 테스트로 갱신한다.
"""

from __future__ import annotations

import random

from maskingtape.pipeline import Pipeline

from bench.generator.variants import _gen_name_long

_CUE = "담당자가 "
_MID = "에서 "
_TAIL = "으로 변경되었습니다. 새 연락처: 010-0000-0000"


def _gen_change_log_doc(rng: random.Random) -> tuple[str, tuple[int, int], tuple[int, int]]:
    first = _gen_name_long(rng)
    second = _gen_name_long(rng)
    text = _CUE + first + _MID + second + _TAIL
    first_start = len(_CUE)
    first_end = first_start + len(first)
    second_start = first_end + len(_MID)
    second_end = second_start + len(second)
    return text, (first_start, first_end), (second_start, second_end)


def test_change_log_second_name_is_currently_missed_known_gap_core_589():
    rng = random.Random("canary:core-589")
    pipeline = Pipeline()
    for _ in range(15):
        text, first_span, second_span = _gen_change_log_doc(rng)
        pred = {(d.kind, d.start, d.end) for d in pipeline.scan(text)}
        first_gold = ("name", *first_span)
        second_gold = ("name", *second_span)

        assert first_gold in pred, (
            f"{text!r}: 첫 번째 이름(`담당자가` 바로 뒤)까지 놓침 — core #589보다 더 심각한 회귀일 수 있음"
        )
        assert second_gold not in pred, (
            f"{text!r}: core #589가 이미 고쳐진 것 같습니다 — "
            "이 테스트를 `assert second_gold in pred`로 갱신하세요"
        )
