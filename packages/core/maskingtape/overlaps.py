# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""겹치는 탐지 구간을 합친다. Pipeline과 마스킹 전략(mask·label·pseudonym)이 함께 쓴다.

치환형 전략(label·pseudonym)은 구간을 뒤에서부터 다른 길이의 문자열로 바꾼다. 겹친 탐지를 그대로
받으면 먼저 바꾼 구간 때문에 위치가 밀려, 바깥 구간의 꼬리가 원문으로 남는다(#494). mask도
keep_head로 구간마다 앞글자를 남기면 뒤 구간의 앞글자가 원문으로 남는다(#520). 그래서 Pipeline을
거치지 않고 apply()를 직접 부를 때도 같은 규칙으로 먼저 합친다.
"""

from __future__ import annotations

from dataclasses import replace

from maskingtape.types import Detection


def resolve_overlaps(detections: list[Detection], text: str) -> list[Detection]:
    """겹치는 탐지 구간을 **합친다**. 어느 쪽도 버리지 않는다.

    비식별화에서 '덜 가리는 것'은 개인정보 유출이고, '더 가리는 것'은 안전한 실패다.
    그래서 겹치면 넓은 쪽(합집합)으로 가리고, 종류(kind)만 확신도가 높은 쪽을 따른다.

    예전에는 겹치는 탐지를 통째로 버렸는데, 주소 탐지기가 뒤따르는 주민등록번호의 앞자리를
    번지로 삼켜 구간이 겹치면 **주민번호 탐지(확신도 1.0)가 사라져 뒷자리가 그대로 노출**됐다:
        "서울특별시 강남구 역삼동 800101-1234560" → "******************01-1234560"
    게다가 그때 scan()은 rrn을 보고하지 않아, 호출자는 주민번호가 없다고 통보받았다.
    """
    ordered = sorted(detections, key=lambda d: (d.start, -(d.end - d.start), -d.confidence))
    result: list[Detection] = []
    for d in ordered:
        if not result or d.start >= result[-1].end:
            result.append(d)
            continue

        previous = result[-1]
        if d.end <= previous.end:
            # 완전 포함 — 넓은 쪽(previous) 구간을 유지한다(더 가리기=안전). 종류(kind)는
            # 부분 겹침과 동일하게 확신도 높은 쪽을 따라, 더 민감한 종류가 감춰져 보고되지
            # 않게 한다(예: address 안에 완전히 든 rrn을 address가 아니라 rrn으로 보고). (#172)
            if d.confidence > previous.confidence:
                result[-1] = replace(previous, kind=d.kind, confidence=d.confidence)
            continue

        # 부분적으로 겹친다 — 가리는 범위는 합집합, 종류는 확신도가 높은 쪽을 남긴다
        winner = d if d.confidence > previous.confidence else previous
        result[-1] = replace(
            winner, start=previous.start, end=d.end, text=text[previous.start : d.end]
        )
    return result
