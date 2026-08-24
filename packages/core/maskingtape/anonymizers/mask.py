# SPDX-License-Identifier: Apache-2.0

"""단순 마스킹 전략 — 탐지 구간을 마스킹 문자로 치환한다."""

from __future__ import annotations

from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.types import Detection


class MaskAnonymizer(Anonymizer):
    """탐지 구간을 같은 길이의 마스킹 문자(기본 '*')로 바꾼다.

    keep_head: 구간 앞에서 보존할 문자 수
               (예: 2면 "800101-1234560" → "80************")
               단, **짧은 값이 통째로 노출되지 않도록** 실제 보존은 구간 길이의 절반을
               넘지 않는다 — 2글자 값은 최대 1글자만 보존한다(#169). keep_head는 파이프라인
               단일 값이라 여러 kind(예: 14자리 RRN과 2글자 이름)에 함께 적용되므로,
               RRN용으로 keep_head=2를 줘도 2글자 이름이 완전 노출되는 일이 없게 한다.
    """

    def __init__(self, mask_char: str = "*", keep_head: int = 0) -> None:
        self.mask_char = mask_char
        self.keep_head = keep_head

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        # 뒤에서부터 치환해야 앞쪽 구간의 위치(start/end)가 밀리지 않는다
        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            span_len = d.end - d.start
            # 최소 절반은 항상 가린다 — 짧은 값(2글자 이름 등)이 keep_head로 통째 노출되는 걸 막는다(#169)
            keep = min(self.keep_head, span_len // 2)
            masked = text[d.start : d.start + keep] + self.mask_char * (span_len - keep)
            text = text[: d.start] + masked + text[d.end :]
        return text
