"""합성 평가 데이터셋(JSONL)을 생성하는 CLI.

사용법:
    python -m bench.generate_dataset --count 500 --seed 42 --out bench/datasets/synth_v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from bench.generator.documents import generate_document


def build_dataset(count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for _ in range(count):
        doc = generate_document(rng)
        rows.append(
            {
                "text": doc.text,
                "labels": [{"kind": lb.kind, "start": lb.start, "end": lb.end} for lb in doc.labels],
            }
        )
    return rows


def write_jsonl(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="합성 개인정보 평가 데이터셋 생성")
    parser.add_argument("--count", type=int, default=200, help="생성할 문서 수")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드 (재현성 보장)")
    parser.add_argument("--out", type=Path, default=Path("bench/datasets/synth_v1.jsonl"))
    args = parser.parse_args()

    rows = build_dataset(args.count, args.seed)
    write_jsonl(rows, args.out)
    print(f"생성 완료: {args.out} ({len(rows)}건, seed={args.seed})")


if __name__ == "__main__":
    main()
