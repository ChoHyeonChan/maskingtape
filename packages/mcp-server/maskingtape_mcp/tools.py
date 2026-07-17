"""MCP 도구의 실제 동작 — 순수 함수로 분리해 MCP 런타임 없이도 테스트한다.

server.py는 이 함수들을 MCP 도구로 등록만 한다 (구조 원칙: 노출과 로직 분리).
"""

from __future__ import annotations

from dataclasses import asdict

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer

# 탐지기는 상태가 없으므로 파이프라인을 재사용한다
_scan_pipeline = Pipeline()


def scan_text(text: str) -> list[dict]:
    """텍스트에서 개인정보를 탐지해 리포트(dict 목록)로 반환한다."""
    return [asdict(d) for d in _scan_pipeline.scan(text)]


def anonymize_text(text: str, strategy: str = "mask") -> str:
    """텍스트의 개인정보를 비식별화해 반환한다.

    strategy: "mask"(*로 가림) 또는 "label"([전화번호] 식 라벨 치환)
    """
    if strategy == "mask":
        pipeline = Pipeline(anonymizer=MaskAnonymizer())
    elif strategy == "label":
        pipeline = Pipeline(anonymizer=LabelAnonymizer())
    else:
        raise ValueError(f"지원하지 않는 strategy: {strategy!r} (mask 또는 label)")
    return pipeline.anonymize(text).text
