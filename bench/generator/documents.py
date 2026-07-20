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

from bench.generator.distractors import generate_distractor
from bench.generator.entities import ALL_KINDS, generate_entity

# distractor는 개인정보가 아니므로 라벨을 붙이지 않는다 — _NON_LABEL_KINDS에서 분기 처리.
_PLACEHOLDER_RE = re.compile(r"\{(name|phone|email|rrn|address|distractor)\}")
_NON_LABEL_KINDS = frozenset({"distractor"})

# 개인정보가 실제로 포함된 템플릿.
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
    # 실제 개인정보 + 헷갈리는 값이 섞인 템플릿 — 엔진이 distractor까지 잘못 잡아내지 않는지 확인.
    "주문번호 {distractor}, 고객 {name}님 {phone}로 발송 예정입니다.",
    "사업자등록번호 {distractor} / 담당자 {name} / 이메일 {email}",
    "결제 금액 {distractor}, 영수증은 {email}로 발송됩니다.",
]

# 개인정보가 전혀 없는(또는 distractor만 있는) 템플릿 — 정답 라벨이 0개인 문서를 만든다.
# false positive(오탐) 측정용: core가 여기서 뭔가를 개인정보로 잘못 찾아내면 그대로 FP로 집계된다.
_NEGATIVE_TEMPLATES = [
    "회의는 내일 오후 2시에 진행됩니다.",
    "이번 분기 매출 목표는 지난해 대비 12% 증가입니다.",
    "서버 점검은 매주 화요일 새벽에 진행됩니다.",
    "주문번호 {distractor}가 정상 접수되었습니다.",
    "사업자등록번호는 {distractor}이며, 배송지 우편번호는 {distractor}입니다.",
    "결제일 {distractor}, 결제 금액 {distractor}.",
    "송장번호 {distractor}로 배송이 시작되었습니다.",
    "다음 회의 안건은 예산 검토와 일정 조정입니다.",
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


def _render(template: str, rng: random.Random) -> Document:
    """템플릿의 {kind} 자리표시자를 채우고, 개인정보 종류만 라벨로 기록한다.

    {distractor}는 개인정보가 아니므로 텍스트에는 삽입하되 라벨은 남기지 않는다 —
    core가 이 구간을 잘못 탐지하면 evaluate.py에서 그대로 FP(오탐)로 집계된다.
    """
    text_parts: list[str] = []
    labels: list[Label] = []
    cursor = 0
    last_end = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        text_parts.append(template[last_end : m.start()])
        cursor += m.start() - last_end

        kind = m.group(1)
        value = generate_distractor(rng) if kind in _NON_LABEL_KINDS else generate_entity(kind, rng).text
        start = cursor
        text_parts.append(value)
        cursor += len(value)
        if kind not in _NON_LABEL_KINDS:
            labels.append(Label(kind=kind, start=start, end=cursor))

        last_end = m.end()

    text_parts.append(template[last_end:])
    return Document(text="".join(text_parts), labels=labels)


def generate_document(rng: random.Random, template: str | None = None) -> Document:
    """실제 개인정보가 포함된 합성 문서 하나를 만든다 (정답 라벨 1개 이상)."""
    return _render(template if template is not None else rng.choice(_TEMPLATES), rng)


def generate_negative_document(rng: random.Random, template: str | None = None) -> Document:
    """개인정보가 없는(또는 distractor만 있는) 합성 문서 하나를 만든다 — 오탐(FP) 측정용, 정답 라벨은 0개."""
    return _render(template if template is not None else rng.choice(_NEGATIVE_TEMPLATES), rng)


def templates() -> list[str]:
    return list(_TEMPLATES)


def negative_templates() -> list[str]:
    return list(_NEGATIVE_TEMPLATES)


__all__ = [
    "ALL_KINDS",
    "Document",
    "Label",
    "generate_document",
    "generate_negative_document",
    "negative_templates",
    "templates",
]
