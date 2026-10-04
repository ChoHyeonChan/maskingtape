# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""문서 성격별 이름 평가 세트(#661) 생성 CLI.

사용법:
    python -m bench.generate_doc_types --out bench/datasets/doc_types_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bench.generator.doc_types import DOC_TYPES, generate_doc_types_dataset

V1_DATASET_NAME = "doc_types_v1.jsonl"
V1_SEED = 661
V1_PER_TYPE = 40


def write_jsonl(rows: list[dict], out_path: Path) -> None:
    """한 줄에 문서 하나씩 쓴다. 한글이 이스케이프되지 않게 ensure_ascii를 끈다."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="문서 성격별 이름 평가 세트(#661) 생성")
    parser.add_argument("--seed", type=int, default=V1_SEED, help="난수 시드 (재현성 보장)")
    parser.add_argument("--per-type", type=int, default=V1_PER_TYPE, help="문서 종류마다 만들 문서 수")
    parser.add_argument("--out", type=Path, default=Path(f"bench/datasets/{V1_DATASET_NAME}"))
    args = parser.parse_args()

    rows = generate_doc_types_dataset(args.seed, args.per_type)
    write_jsonl(rows, args.out)
    print(f"생성 완료: {args.out} ({len(rows)}건, 문서 종류 {len(DOC_TYPES)}개, seed={args.seed})")


if __name__ == "__main__":
    main()
