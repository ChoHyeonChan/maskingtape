# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""프롬프트 공격 골든셋(#549) 생성 CLI.

사용법:
    python -m bench.generate_attacks --out bench/datasets/attacks_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bench.generator.attacks import generate_attack_dataset

V1_DATASET_NAME = "attacks_v1.jsonl"


def write_jsonl(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="프롬프트 공격 골든셋(#549) 생성")
    parser.add_argument("--seed", type=int, default=549, help="난수 시드 (재현성 보장)")
    parser.add_argument("--per-tag", type=int, default=20, help="공격 종류마다 만들 쌍(깨끗한 판+공격 판)의 수")
    parser.add_argument("--out", type=Path, default=Path(f"bench/datasets/{V1_DATASET_NAME}"))
    args = parser.parse_args()

    rows = generate_attack_dataset(args.seed, args.per_tag)
    write_jsonl(rows, args.out)
    tags = sorted({row["attack_tag"] for row in rows} - {"none"})
    print(f"생성 완료: {args.out} ({len(rows)}건 = {len(rows) // 2}쌍, 공격 {len(tags)}종, seed={args.seed})")


if __name__ == "__main__":
    main()
