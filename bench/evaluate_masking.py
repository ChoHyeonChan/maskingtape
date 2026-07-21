"""마스킹 결과물 자체의 안전성(개인정보 유출 여부)을 평가하는 CLI.

evaluate.py가 "탐지 위치가 정답과 일치하는가"를 보는 내부 지표라면,
이 스크립트는 "실제로 사용자가 받는 최종 텍스트에 개인정보가 남아있는가"를
검사하는 산출물 지표다 — 탐지를 놓쳤든 마스킹 로직에 버그가 있든 결과(유출)는 동일하게 잡힌다.

사용법:
    python -m bench.evaluate_masking bench/datasets/synth_v1.jsonl
"""

from __future__ import annotations

import argparse
from pathlib import Path

from maskingtape.pipeline import Pipeline

from bench.evaluate import load_dataset
from bench.mask_quality import evaluate_mask_quality, format_mask_quality_report


def main() -> None:
    parser = argparse.ArgumentParser(description="합성 데이터셋으로 마스킹 결과물의 개인정보 유출 여부 평가")
    parser.add_argument("dataset", type=Path, help="평가할 JSONL 데이터셋 경로")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    result = evaluate_mask_quality(rows, Pipeline())
    print(format_mask_quality_report(result))


if __name__ == "__main__":
    main()
