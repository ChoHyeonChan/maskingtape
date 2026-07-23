"""MCP 도구의 실제 동작 — 순수 함수로 분리해 MCP 런타임 없이도 테스트한다.

server.py는 이 함수들을 MCP 도구로 등록만 한다 (구조 원칙: 노출과 로직 분리).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer

from maskingtape_mcp.safe_file import read_text_file, write_masked_copy

# 탐지기는 상태가 없으므로 파이프라인을 재사용한다
_scan_pipeline = Pipeline()


def _build_pipeline(strategy: str, numbered: bool) -> Pipeline:
    """strategy/numbered 조합으로 파이프라인을 만든다. 잘못된 strategy는 ValueError."""
    if strategy == "mask":
        return Pipeline(anonymizer=MaskAnonymizer())
    if strategy == "label":
        return Pipeline(anonymizer=LabelAnonymizer(numbered=numbered))
    raise ValueError(f"지원하지 않는 strategy: {strategy!r} (mask 또는 label)")


def scan_text(text: str) -> list[dict]:
    """텍스트에서 개인정보를 탐지해 리포트(dict 목록)로 반환한다."""
    return [asdict(d) for d in _scan_pipeline.scan(text)]


def anonymize_text(text: str, strategy: str = "mask", numbered: bool = False) -> str:
    """텍스트의 개인정보를 비식별화해 반환한다.

    strategy: "mask"(*로 가림) 또는 "label"([전화번호] 식 라벨 치환)
    numbered: label 전략에서 같은 값을 같은 번호로 치환할지([이름1] 등).
              같은 사람·번호가 문서 안에서 일관되게 유지돼 LLM 문맥 보존에 유리하다.
    """
    return _build_pipeline(strategy, numbered).anonymize(text).text


def anonymize_file(path: str, strategy: str = "mask", numbered: bool = False) -> dict:
    """텍스트 파일을 읽어 비식별화한 사본을 `<이름>_masked.<확장자>`로 저장한다.

    AI 에이전트가 로컬 파일을 외부로 보내기 전 통째로 비식별화할 때 쓴다.
    반환: 입력/출력 경로, 탐지 총건수, 종류별 건수 요약.

    파일 접근 제한(심볼릭 링크 거부·덮어쓰기 금지·크기 상한·UTF-8만)은
    safe_file 모듈이 담당한다 — 에이전트가 조작돼도 파일이 파괴되지 않게 한다.
    """
    src, text = read_text_file(path)
    result = _build_pipeline(strategy, numbered).anonymize(text)
    dst = write_masked_copy(src, result.text)

    by_kind = Counter(d.kind for d in result.detections)
    return {
        "input": str(src),
        "output": str(dst),
        "detections": len(result.detections),
        "by_kind": dict(by_kind),
    }
