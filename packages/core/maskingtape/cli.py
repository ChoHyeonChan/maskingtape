"""CLI 진입점 — `maskingtape "텍스트"` 또는 파이프 입력을 마스킹해 출력한다.

사용 예:
    maskingtape "주민번호 800101-1234560 문의주세요"
    type 문서.txt | maskingtape        (Windows) / cat 문서.txt | maskingtape
    maskingtape --scan "..."            # 마스킹 없이 탐지 리포트만(JSON)
    maskingtape --strategy label "..."  # [전화번호] 식 라벨 치환
    maskingtape --llm "..."             # 이름을 로컬 LLM으로 판단 (Ollama 필요)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from maskingtape.anonymizers import LabelAnonymizer, MaskAnonymizer
from maskingtape.detectors import DEFAULT_MODEL, llm_detectors
from maskingtape.pipeline import Pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="maskingtape", description="한국어 개인정보 비식별화 엔진"
    )
    parser.add_argument("text", nargs="?", help="입력 텍스트 (생략 시 표준입력에서 읽음)")
    parser.add_argument(
        "--scan", action="store_true", help="마스킹 없이 탐지 결과만 JSON으로 출력"
    )
    parser.add_argument(
        "--strategy",
        choices=["mask", "label"],
        default="mask",
        help="비식별화 전략: mask(*로 가림, 기본) 또는 label([전화번호] 식 치환)",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="이름을 규칙 대신 로컬 LLM으로 판단한다 (로컬 Ollama 실행 필요)",
    )
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_MODEL,
        help=f"--llm이 쓸 Ollama 모델 (기본: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    anonymizer = LabelAnonymizer() if args.strategy == "label" else MaskAnonymizer()
    detectors = llm_detectors(model=args.llm_model) if args.llm else None
    pipeline = Pipeline(detectors=detectors, anonymizer=anonymizer)

    try:
        detections = pipeline.scan(text)
    except RuntimeError as exc:  # --llm인데 Ollama가 없는 등 — 무엇을 고쳐야 하는지 알린다
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.scan:
        print(json.dumps([asdict(d) for d in detections], ensure_ascii=False, indent=2))
    else:
        print(anonymizer.apply(text, detections))
    return 0


if __name__ == "__main__":
    sys.exit(main())
