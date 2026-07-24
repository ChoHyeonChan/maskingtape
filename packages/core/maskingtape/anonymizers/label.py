"""라벨 치환 전략 — 탐지 구간을 종류별 라벨로 바꾼다.

마스킹(*)과 달리 "어떤 종류의 정보가 있었는지"가 보존되므로,
LLM에 넘기기 전 전처리나 로그 비식별화에 적합하다.
    예: "연락처 010-1234-5678" → "연락처 [전화번호]"

numbered=True면 서로 다른 값마다 번호를 붙인다: [전화번호1], [전화번호2]
같은 값은 같은 번호를 받아 문맥상 동일 인물/번호라는 정보가 유지된다.
"""

from __future__ import annotations

from collections.abc import Sequence

from maskingtape.anonymizers.base import Anonymizer
from maskingtape.types import Detection

DEFAULT_LABELS = {
    "rrn": "주민등록번호",
    "phone": "전화번호",
    "email": "이메일",
    "name": "이름",
    "address": "주소",
    "card": "카드번호",
}


class LabelAnonymizer(Anonymizer):
    """탐지 구간을 `[라벨]` 형태로 치환한다."""

    def __init__(self, labels: dict[str, str] | None = None, numbered: bool = False) -> None:
        self.labels = {**DEFAULT_LABELS, **(labels or {})}
        self.numbered = numbered

    def apply(self, text: str, detections: Sequence[Detection]) -> str:
        # 번호는 등장 순서(앞→뒤)로 매기고, 치환은 위치가 안 밀리게 뒤→앞으로 한다
        numbers: dict[tuple[str, str], int] = {}
        if self.numbered:
            for d in sorted(detections, key=lambda d: d.start):
                key = (d.kind, d.text)
                if key not in numbers:
                    numbers[key] = sum(1 for k in numbers if k[0] == d.kind) + 1

        for d in sorted(detections, key=lambda d: d.start, reverse=True):
            label = self.labels.get(d.kind, d.kind)
            if self.numbered:
                label = f"{label}{numbers[(d.kind, d.text)]}"
            text = text[: d.start] + f"[{label}]" + text[d.end :]
        return text
