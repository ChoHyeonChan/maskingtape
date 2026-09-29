# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""단순 마스킹 전략 — 탐지 구간을 마스킹 문자로 치환한다."""

from __future__ import annotations

from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.normalize import normalize
from maskingtape.overlaps import resolve_overlaps
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
        """mask_char는 가릴 때 쓸 문자, keep_head는 앞에서 남길 글자 수다.

        keep_head는 실제로는 구간 길이의 절반까지만 적용된다(클래스 설명, #169).
        """
        self.mask_char = mask_char
        self.keep_head = keep_head

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        """구간마다 앞 keep_head 글자(최대 절반)만 남기고 나머지를 마스킹 문자로 바꾼다.

        겹친 탐지는 먼저 합친다. 구간마다 앞글자를 남기면 뒤 구간의 앞글자가 원문으로 남는다(#520).
        """
        detections = resolve_overlaps(list(detections), text)
        # 뒤에서부터 치환해야 앞쪽 구간의 위치(start/end)가 밀리지 않는다
        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            span_len = d.end - d.start
            keep = self._kept_length(text[d.start : d.end])
            masked = text[d.start : d.start + keep] + self.mask_char * (span_len - keep)
            text = text[: d.start] + masked + text[d.end :]
        return text

    def _kept_length(self, segment: str) -> int:
        """구간 앞에서 남길 글자 수(원문 글자 기준)를 정한다.

        최소 절반은 항상 가린다 — 짧은 값(2글자 이름 등)이 keep_head로 통째 노출되는 걸
        막는다(#169). 글자 수는 표기 정리의 글자 묶음 단위로 센다(#490). 폭 없는 공백이
        끼거나, 자모로 분해됐거나, 합쳐지지 않는 자모가 음절 뒤에 붙으면 원문 코드포인트가
        늘어 절반이 커지고 이름 글자가 더 드러나기 때문이다.
        """
        if self.keep_head <= 0:
            return 0
        prepared = normalize(segment)
        if prepared.starts is None:
            return min(self.keep_head, len(segment) // 2)
        units = sorted(set(prepared.starts))  # 글자 묶음마다 원문 시작 위치
        count = min(self.keep_head, len(units) // 2)
        if count == 0:
            return 0
        return units[count] if count < len(units) else len(segment)
