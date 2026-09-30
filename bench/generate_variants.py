# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""표기 변형 평가 세트(#531) 생성 CLI.

사용법:
    python -m bench.generate_variants --out bench/datasets/variants_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bench.generator.variants import generate_variants_dataset

V1_DATASET_NAME = "variants_v1.jsonl"


def write_jsonl(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="표기 변형 평가 세트(#531) 생성")
    parser.add_argument("--seed", type=int, default=531, help="난수 시드 (재현성 보장)")
    parser.add_argument("--per-tag", type=int, default=15, help="표기 태그마다 만들 문서 수")
    parser.add_argument("--out", type=Path, default=Path(f"bench/datasets/{V1_DATASET_NAME}"))
    args = parser.parse_args()

    rows = generate_variants_dataset(args.seed, args.per_tag)
    write_jsonl(rows, args.out)
    tags = sorted({row["variant_tag"] for row in rows})
    print(f"생성 완료: {args.out} ({len(rows)}건, {len(tags)}개 표기 태그, seed={args.seed})")


if __name__ == "__main__":
    main()
