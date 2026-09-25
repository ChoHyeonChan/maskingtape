# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""합성 평가 데이터셋(JSONL)을 생성하는 CLI.

사용법:
    python -m bench.generate_dataset --count 500 --seed 42 --out bench/datasets/synth_v1.jsonl
    python -m bench.generate_dataset --count 500 --seed 42 --address-extended --out bench/datasets/synth_v2.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from bench.generator.documents import (
    generate_document,
    generate_multi_sentence_document,
    generate_negative_document,
)

# 제출 보고서·README 정확도 수치의 근거 데이터셋. 이 파일은 기본 옵션 + 시드만으로 다시 만들 수 있어야 한다.
V1_DATASET_NAME = "synth_v1.jsonl"


def build_dataset(
    count: int,
    seed: int,
    negative_ratio: float = 0.25,
    multi_sentence_ratio: float = 0.15,
    address_extended: bool = False,
) -> list[dict]:
    """negative_ratio 비율만큼은 개인정보 없는(오탐 측정용) 문서로, 그 나머지 중
    multi_sentence_ratio 비율만큼은 여러 문장을 이어붙인 복합 문서로 채운다.

    address_extended=True면 core #423이 고친 주소 형태도 섞는다(#431) — 난수 흐름이 달라져
    v1과 다른 데이터셋이 되므로 반드시 새 파일로 저장한다.
    """
    rng = random.Random(seed)
    rows = []
    for _ in range(count):
        if rng.random() < negative_ratio:
            doc = generate_negative_document(rng)
        elif rng.random() < multi_sentence_ratio:
            doc = generate_multi_sentence_document(rng, address_extended=address_extended)
        else:
            doc = generate_document(rng, address_extended=address_extended)
        rows.append(
            {
                "text": doc.text,
                "labels": [{"kind": lb.kind, "start": lb.start, "end": lb.end} for lb in doc.labels],
                "difficulty": doc.difficulty,
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
    parser.add_argument(
        "--negative-ratio",
        type=float,
        default=0.25,
        help="개인정보가 전혀 없는 오탐(FP) 측정용 문서 비율 (0~1)",
    )
    parser.add_argument(
        "--multi-sentence-ratio",
        type=float,
        default=0.15,
        help="여러 문장을 이어붙인 복합 문서 비율 — negative가 아닌 문서 중에서 (0~1)",
    )
    parser.add_argument(
        "--address-extended",
        action="store_true",
        help="core #423이 고친 주소 형태(읍·면 뒤 도로명·리, 동·리가 든 도로명, N가 동 등)도 섞는다(#431). "
        "v1과 다른 데이터셋이라 새 파일로 저장해야 한다.",
    )
    parser.add_argument("--out", type=Path, default=Path(f"bench/datasets/{V1_DATASET_NAME}"))
    args = parser.parse_args()

    if args.address_extended and args.out.name == V1_DATASET_NAME:
        parser.error(
            f"--address-extended는 v1과 다른 데이터셋을 만든다. {V1_DATASET_NAME}을 덮어쓰면 제출 수치의 "
            "근거가 사라지니 --out을 새 파일(예: bench/datasets/synth_v2.jsonl)로 지정할 것"
        )

    rows = build_dataset(
        args.count, args.seed, args.negative_ratio, args.multi_sentence_ratio, args.address_extended
    )
    write_jsonl(rows, args.out)
    print(f"생성 완료: {args.out} ({len(rows)}건, seed={args.seed})")


if __name__ == "__main__":
    main()
