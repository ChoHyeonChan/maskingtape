"""CLI 진입점 — `maskingtape "텍스트"` 또는 파이프 입력을 마스킹해 출력한다.

사용 예:
    maskingtape "주민번호 800101-1234560 문의주세요"
    type 문서.txt | maskingtape        (Windows) / cat 문서.txt | maskingtape
    maskingtape --scan "..."            # 마스킹 없이 탐지 리포트만(JSON)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from maskingtape.pipeline import Pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="maskingtape", description="한국어 개인정보 비식별화 엔진"
    )
    parser.add_argument("text", nargs="?", help="입력 텍스트 (생략 시 표준입력에서 읽음)")
    parser.add_argument(
        "--scan", action="store_true", help="마스킹 없이 탐지 결과만 JSON으로 출력"
    )
    args = parser.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    pipeline = Pipeline()

    if args.scan:
        report = [asdict(d) for d in pipeline.scan(text)]
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(pipeline.anonymize(text).text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
