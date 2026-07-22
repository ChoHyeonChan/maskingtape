"""MCP 도구의 실제 동작 — 순수 함수로 분리해 MCP 런타임 없이도 테스트한다.

server.py는 이 함수들을 MCP 도구로 등록만 한다 (구조 원칙: 노출과 로직 분리).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer

# 탐지기는 상태가 없으므로 파이프라인을 재사용한다
_scan_pipeline = Pipeline()

# 파일 크기 상한 — MCP 도구가 실수로 거대 파일을 통째로 메모리에 올리는 걸 막는다
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10MB


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

    strategy/numbered는 anonymize_text와 동일. 파일은 UTF-8로 읽고 쓴다
    (다른 인코딩이면 명확한 오류를 낸다 — 조용히 깨진 결과를 저장하지 않는다).
    """
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    size = src.stat().st_size
    if size > _MAX_FILE_BYTES:
        raise ValueError(f"파일이 너무 큽니다({size} bytes, 상한 {_MAX_FILE_BYTES} bytes)")

    try:
        text = src.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"UTF-8로 읽을 수 없는 파일입니다: {path} (텍스트 파일인지, 인코딩이 UTF-8인지 확인하세요)"
        ) from exc

    result = _build_pipeline(strategy, numbered).anonymize(text)

    dst = src.with_name(f"{src.stem}_masked{src.suffix}")
    dst.write_text(result.text, encoding="utf-8")

    by_kind = Counter(d.kind for d in result.detections)
    return {
        "input": str(src),
        "output": str(dst),
        "detections": len(result.detections),
        "by_kind": dict(by_kind),
    }
