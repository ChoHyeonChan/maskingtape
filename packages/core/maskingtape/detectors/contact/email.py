# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이메일 주소 탐지기 — 표준 형태의 이메일을 정규식으로 찾는다.

로컬 파트에 한글을 허용한다(#400). RFC 6531(SMTPUTF8)이 국제화 주소를 규정하고
국내 일부 서비스가 실제로 발급한다. 한국어 특화 도구가 한글 이메일을 놓치면
그대로 유출이다.

**도메인부는 영문 규칙 그대로 둔다.** 한글 도메인까지 넓히면 `회의@3층`,
`가격@10000원` 같은 평범한 한국어 표현이 전부 이메일로 잡힌다. 로컬 파트만
넓히고 도메인이 `영문라벨.영문TLD`인지 검사하는 것이 오탐을 막는 핵심이다.

**알려진 한계 — 앞 글자를 삼킨다.** 한국어는 조사가 붙어 띄어쓰기 없이 이어지므로
`담당자는홍길동@example.com`에서 로컬 파트가 `담당자는홍길동`으로 잡힌다. 정규식은
각 위치에서 매치를 시도하기 때문에 lookbehind로도 막을 수 없고, 형태만으로는
`담당자는`이 조사인지 주소의 일부인지 구분할 방법이 없다. 결과는 **과다 마스킹**이라
개인정보가 새지는 않는다(덜 가리기는 유출, 더 가리기는 안전). 실제 문서는 이메일
앞에 공백이나 문장부호를 두는 경우가 대부분이라 영향이 크지 않다.

보안(ReDoS 방지): 모든 반복에 상한을 둔다. 상한이 없으면 `@`가 없는 긴 문자열
("0"을 40만 자 등)에서 각 시작 위치마다 뒤를 전부 삼켰다가 실패하는 일이 반복돼
처리 시간이 입력 길이의 제곱으로 늘어난다(실측 40만 자 1.4초 → 서비스 거부 가능).
상한은 RFC 5321의 실제 한계라 정상 이메일은 그대로 탐지된다. 한글을 더해도
문자 클래스가 넓어질 뿐 반복 상한은 그대로라 이 방어는 유지된다.
"""

from __future__ import annotations

import re

from maskingtape.detectors.base import Detector
from maskingtape.types import Detection

_EMAIL_RE = re.compile(
    # 로컬 파트 — 영숫자·기호에 한글을 더했다(RFC 6531). 상한 64자는 RFC 5321 한계이자
    # ReDoS 방어선이라 그대로 둔다. 한글은 UTF-8에서 3바이트지만 여기서는 문자 수로 센다.
    r"[A-Za-z0-9._%+\-가-힣]{1,64}"
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
