"""이메일 주소 탐지기 — 표준 형태의 이메일을 정규식으로 찾는다.

보안(ReDoS 방지): 모든 반복에 상한을 둔다. 상한이 없으면 `@`가 없는 긴 문자열
("0"을 40만 자 등)에서 각 시작 위치마다 뒤를 전부 삼켰다가 실패하는 일이 반복돼
처리 시간이 입력 길이의 제곱으로 늘어난다(실측 40만 자 1.4초 → 서비스 거부 가능).
상한은 RFC 5321의 실제 한계라 정상 이메일은 그대로 탐지된다.
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]{1,64}"  # 로컬 파트 (RFC 5321: 최대 64자)
    r"@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.){1,8}"  # 도메인 라벨 (라벨당 최대 63자)
    r"[A-Za-z]{2,63}"  # 최상위 도메인
)


class EmailDetector(Detector):
    """이메일 주소 탐지기."""

    kind = "email"

    def detect(self, text: str) -> list[Detection]:
        return [
            Detection(
                kind=self.kind,
                start=m.start(),
                end=m.end(),
                text=m.group(0),
                confidence=1.0,
                detector=self.__class__.__name__,
            )
            for m in _EMAIL_RE.finditer(text)
        ]
