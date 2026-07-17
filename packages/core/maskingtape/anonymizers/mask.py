"""단순 마스킹 전략 — 탐지 구간을 마스킹 문자로 치환한다."""

from __future__ import annotations

from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.types import Detection


class MaskAnonymizer(Anonymizer):
    """탐지 구간을 같은 길이의 마스킹 문자(기본 '*')로 바꾼다.

    keep_head: 구간 앞에서 보존할 문자 수
               (예: 2면 "800101-1234560" → "80************")
    """

    def __init__(self, mask_char: str = "*", keep_head: int = 0) -> None:
        self.mask_char = mask_char
        self.keep_head = keep_head

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        # 뒤에서부터 치환해야 앞쪽 구간의 위치(start/end)가 밀리지 않는다
        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            span_len = d.end - d.start
            keep = min(self.keep_head, span_len)
            masked = text[d.start : d.start + keep] + self.mask_char * (span_len - keep)
            text = text[: d.start] + masked + text[d.end :]
        return text
