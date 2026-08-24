# SPDX-License-Identifier: Apache-2.0

"""MCP 도구의 실제 동작 — 순수 함수로 분리해 MCP 런타임 없이도 테스트한다.

server.py는 이 함수들을 MCP 도구로 등록만 한다 (구조 원칙: 노출과 로직 분리).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict

from maskingtape import Pipeline
from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer, PseudonymAnonymizer
from maskingtape.detectors import llm_detectors

from maskingtape_mcp.safe_file import read_text_file, write_masked_copy

# LLM(하이브리드) 탐지 사용 여부. 서버 레벨 결정 — server.py가 --llm에 따라 한 번 set_llm_mode를 부른다.
# 도구 파라미터가 아니라 서버 설정으로 두는 이유: MCP는 "에이전트가 조작된다"고 가정하므로,
# 조작된 에이전트가 마스킹 강도를 낮추지 못하게 신뢰 주체(서버 세운 사람)가 정한다.
_use_llm = False


def set_llm_mode(enabled: bool) -> None:
    """LLM(하이브리드) 탐지 사용 여부를 설정한다.

    기본(False)은 규칙 전용 — Ollama 없이 어디서나 동작하는 안전 바닥. True면 이름을
    로컬 LLM으로 문맥 판단하는 llm_detectors()를 쓴다(**로컬 Ollama 필요**).
    Ollama가 없으면 호출 시 명확히 에러난다 — 조용히 규칙으로 강등하지 않는다
    (하이브리드인 줄 알고 이름이 새는 silent downgrade를 막기 위함).
    """
    global _use_llm
    _use_llm = enabled


def _detectors():
    """현재 모드에 맞는 탐지기 세트. None이면 Pipeline이 규칙 전용 기본(default_detectors)을 쓴다."""
    return llm_detectors() if _use_llm else None


def _build_pipeline(strategy: str, numbered: bool) -> Pipeline:
    """strategy/numbered 조합으로 파이프라인을 만든다. 잘못된 strategy는 ValueError."""
    detectors = _detectors()
    if strategy == "mask":
        return Pipeline(detectors=detectors, anonymizer=MaskAnonymizer())
    if strategy == "label":
        return Pipeline(detectors=detectors, anonymizer=LabelAnonymizer(numbered=numbered))
    if strategy == "pseudonym":
        # 그럴듯한 가짜 값으로 치환. numbered는 label 전용이라 여기선 쓰지 않는다 —
        # pseudonym은 같은 값→같은 가짜값을 자체적으로 유지한다.
        return Pipeline(detectors=detectors, anonymizer=PseudonymAnonymizer())
    raise ValueError(f"지원하지 않는 strategy: {strategy!r} (mask, label, pseudonym)")


def _report(detection) -> dict:
    """탐지 리포트 dict — 종류·위치·확신도만. **원문 PII 값(text)은 싣지 않는다**(데이터 최소화).

    에이전트는 start/end로 필요하면 원문을 잘라볼 수 있고, 리포트를 로그·외부로 넘겨도
    원문 개인정보가 함께 새지 않는다(리포트를 "안전한 요약"으로 오인하는 footgun 차단).
    """
    report = asdict(detection)
    report.pop("text", None)
    return report


def scan_text(text: str) -> list[dict]:
    """텍스트에서 개인정보를 탐지해 리포트(종류·위치·확신도)를 반환한다."""
    return [_report(d) for d in Pipeline(detectors=_detectors()).scan(text)]


def anonymize_text(text: str, strategy: str = "mask", numbered: bool = False) -> str:
    """텍스트의 개인정보를 비식별화해 반환한다.

    strategy: "mask"(*로 가림) / "label"([전화번호] 식 라벨 치환) /
              "pseudonym"(그럴듯한 가짜 값으로 치환 — 문맥이 살아 LLM 처리·데이터셋 공유에 유리)
    numbered: label 전략에서 같은 값을 같은 번호로 치환할지([이름1] 등).
              같은 사람·번호가 문서 안에서 일관되게 유지돼 LLM 문맥 보존에 유리하다.
              (pseudonym은 자체적으로 같은 값→같은 가짜값을 유지하므로 이 옵션과 무관하다.)
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
