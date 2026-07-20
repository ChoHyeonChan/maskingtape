"""문장 템플릿에 개인정보 값을 심어 문서(JSONL 한 줄)를 만든다.

동작 원리:
1. 템플릿 문자열의 {kind} 자리표시자를 순서대로 찾는다.
2. 각 자리표시자를 entities.generate_entity()가 만든 값으로 치환하면서
   현재까지 조립된 텍스트 길이로 start/end(파이썬 슬라이스 규약)를 계산한다.
3. 치환이 끝난 전체 텍스트와 라벨 목록을 함께 반환한다 — bench/README.md의 데이터셋 포맷 계약을 따른다.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from bench.generator.entities import ALL_KINDS, generate_entity

_PLACEHOLDER_RE = re.compile(r"\{(name|phone|email|rrn|address)\}")

_TEMPLATES = [
    "고객 {name}님 {phone}로 연락 부탁드립니다.",
    "신청자: {name} / 연락처: {phone} / 이메일: {email}",
    "{name} 환자분, 주민등록번호 {rrn} 확인되었습니다.",
    "배송지: {address} (수령인 {name}, {phone})",
    "{email}로 회신 주시면 {name} 담당자가 답변드립니다.",
    "긴급 연락처 {phone}, 자택 주소는 {address}입니다.",
    "본인확인용 주민번호 {rrn}와 이메일 {email}을 제출합니다.",
    "안녕하세요, 저는 {name}이고 전화번호는 {phone}입니다.",
    "{address}에 거주하는 {name}님께 우편을 발송했습니다.",
    "오늘 회의록: 작성자 {name}, 문의는 {email}로.",
]


@dataclass(frozen=True)
class Label:
    kind: str
    start: int
    end: int


@dataclass(frozen=True)
class Document:
    text: str
    labels: list[Label]


def generate_document(rng: random.Random, template: str | None = None) -> Document:
    """템플릿 하나를 골라 개인정보 값을 채운 합성 문서 하나를 만든다."""
    template = template if template is not None else rng.choice(_TEMPLATES)

    text_parts: list[str] = []
    labels: list[Label] = []
    cursor = 0
    last_end = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        text_parts.append(template[last_end : m.start()])
        cursor += m.start() - last_end

        entity = generate_entity(m.group(1), rng)
        start = cursor
        text_parts.append(entity.text)
        cursor += len(entity.text)
        labels.append(Label(kind=entity.kind, start=start, end=cursor))

        last_end = m.end()

    text_parts.append(template[last_end:])
    text = "".join(text_parts)
    return Document(text=text, labels=labels)


def templates() -> list[str]:
    return list(_TEMPLATES)


__all__ = ["ALL_KINDS", "Document", "Label", "generate_document", "templates"]
