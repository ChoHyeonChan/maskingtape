# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 보고용 세트(#456) 생성 CLI.

사용법:
    python -m bench.generate_doc_types_holdout --out bench/datasets/doc_types_holdout_v1.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bench.generate_doc_types import write_jsonl
from bench.generator.doc_types_holdout import HOLDOUT_DOC_TYPES, generate_holdout_dataset

HOLDOUT_DATASET_NAME = "doc_types_holdout_v1.jsonl"
HOLDOUT_SEED = 456
HOLDOUT_PER_TYPE = 40


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="문서 성격별 보고용 세트(#456) 생성")
    parser.add_argument("--seed", type=int, default=HOLDOUT_SEED, help="난수 시드 (재현성 보장)")
    parser.add_argument("--per-type", type=int, default=HOLDOUT_PER_TYPE, help="문서 종류마다 만들 문서 수")
    parser.add_argument("--out", type=Path, default=Path(f"bench/datasets/{HOLDOUT_DATASET_NAME}"))
    args = parser.parse_args()

    rows = generate_holdout_dataset(args.seed, args.per_type)
    write_jsonl(rows, args.out)
    print(f"생성 완료: {args.out} ({len(rows)}건, 문서 종류 {len(HOLDOUT_DOC_TYPES)}개, seed={args.seed})")


if __name__ == "__main__":
    main()
