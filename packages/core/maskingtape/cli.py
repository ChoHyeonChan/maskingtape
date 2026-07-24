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


def _use_utf8_output() -> None:
    """표준출력·표준오류를 UTF-8로 고정한다.

    Windows 콘솔 기본값(cp949)이면 한글이 깨지고, cp949로 표현할 수 없는 문자(이모지 등)가
    하나만 있어도 UnicodeEncodeError로 죽어 마스킹 결과를 아예 받지 못한다.
    리다이렉트한 파일도 cp949로 저장돼 UTF-8을 기대하는 다음 단계가 깨진다.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def _read_stdin() -> str:
    """표준입력을 UTF-8로 읽는다.

    보안: 인코딩을 콘솔 기본값(Windows에서 cp949)에 맡기면 UTF-8 문서가 잘못 디코딩돼
    한글이 깨지고, 한글에 의존하는 이름·주소 탐지가 통째로 실패한다. 숫자(주민등록번호·
    전화번호)는 ASCII라 살아남으므로 **동작하는 것처럼 보이면서 이름만 유출**된다.
    그래서 UTF-8로 명시해 읽고, 디코딩할 수 없으면 조용히 잘못 읽지 않고 멈춘다 —
    부분만 마스킹된 결과를 돌려주는 것이 가장 위험하다.
    """
    return sys.stdin.buffer.read().decode("utf-8")


def main() -> int:
    _use_utf8_output()
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

    if args.text is not None:
        text = args.text
    else:
        try:
            text = _read_stdin()
        except UnicodeDecodeError:
            print(
                "오류: 표준입력을 UTF-8로 읽지 못했습니다. 입력을 UTF-8로 저장한 뒤 다시 시도하세요.\n"
                "      (다른 인코딩을 그대로 읽으면 한글이 깨져 이름·주소가 마스킹되지 않습니다)",
                file=sys.stderr,
            )
            return 2

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
