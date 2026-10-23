# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII를 Zenodo에서 받아 평가용 jsonl로 바꾸는 CLI.

KDPII(한국어 대화 개인정보 데이터셋, https://doi.org/10.5281/zenodo.10968609, CC-BY-4.0)는 README의
이름 하이브리드 외부 비교와 타 도구 비교(`bench/evaluators/compare_kdpii_tools.py`)에 쓴다. 원자료와
변환본은 저장소에 싣지 않는다(SBOM 부록 D). 대신 누가 받아도 같은 파일이 되도록, 받은 파일의 크기와
MD5를 Zenodo에 적힌 값과 대조하고 한 줄에 한 문장씩 원본 순서대로 쓴다.

KDPII 라벨 중 우리 11종에 대응하는 것은 bench 형식의 `labels`(종류·구간·원래 라벨)로, 나머지(직장·직위·
닉네임 등)는 `other`로 둔다. `other`는 재현율에는 안 쓰고 「개인정보가 아닌 곳을 가렸나」를 셀 때만 쓴다.

사용법:
    python -m bench.fetch_kdpii --split test
    python -m bench.fetch_kdpii --split test --name-sample 500   # 이름 하이브리드 외부 비교용 500문장도 쓴다
    python -m bench.fetch_kdpii --split test --raw test.json     # 이미 받은 파일을 바꾸기만 할 때
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import urllib.request
from pathlib import Path
from typing import BinaryIO

RECORD_URL = "https://zenodo.org/api/records/10968609/files/{split}.json/content"
# Zenodo 레코드 10968609에 적힌 파일별 MD5와 바이트 수(2026-10-20 확인)
MD5 = {
    "train": "fa633403055e4e5918b92b2d11726434",
    "valid": "6f89923f873c840ca773d255d058150c",
    "test": "08eebd98593c1bad23fbf29053b3f9d2",
}
SIZE = {"train": 49_798_233, "valid": 6_260_192, "test": 6_124_918}
# 어디서 실행해도 bench/datasets/external(.gitignore에 있다)에 쓴다
OUT_DIR = Path(__file__).resolve().parent / "datasets" / "external"

# KDPII 라벨 → maskingtape 종류. 여기 없는 라벨은 other로 간다. 사업자등록번호는 KDPII에 없다.
KDPII_TO_KIND = {
    "PS_NAME": "name",
    "QT_PHONE": "phone",
    "QT_MOBILE": "phone",
    "TMI_EMAIL": "email",
    "QT_RESIDENT_NUMBER": "rrn",
    "QT_ALIEN_NUMBER": "rrn",
    "LC_ADDRESS": "address",
    "QT_CARD_NUMBER": "card",
    "QT_ACCOUNT_NUMBER": "account",
    "QT_PASSPORT_NUMBER": "passport",
    "QT_DRIVER_NUMBER": "driver_license",
    "DT_BIRTH": "birth_date",
}
# README 이름 하이브리드 외부 비교(2026-10-04)에 쓴 표본의 시드
NAME_SAMPLE_SEED = 458


def read_capped(stream: BinaryIO, limit: int) -> bytes:
    """끝까지 1MB씩 읽되, limit을 넘으면 멈춘다. 응답이 선언한 크기는 믿지 않는다."""
    chunks, total = [], 0
    while chunk := stream.read(1 << 20):
        total += len(chunk)
        if total > limit:
            raise ValueError(f"응답이 {limit}바이트보다 크다")
        chunks.append(chunk)
    return b"".join(chunks)


def check_md5(data: bytes, split: str) -> None:
    if len(data) != SIZE[split]:
        raise ValueError(f"{split}.json 크기가 Zenodo 값과 다르다: {len(data)} != {SIZE[split]}")
    digest = hashlib.md5(data).hexdigest()
    if digest != MD5[split]:
        raise ValueError(f"{split}.json MD5가 Zenodo 값과 다르다: {digest} != {MD5[split]}")


def to_rows(records: list[dict]) -> list[dict]:
    """KDPII 문장 레코드를 bench 형식으로 바꾼다. 구간이 원문과 안 맞으면 멈춘다."""
    rows = []
    for r in records:
        text = r["sentence"]
        labels, other = [], []
        for p in r["PII_set"]:
            if text[p["begin"] : p["end"]] != p["form"]:
                raise ValueError(f"{r['sent_idx']}: 구간 {p['begin']}~{p['end']}이 원문과 다르다")
            item = {"start": p["begin"], "end": p["end"], "raw": p["label"]}
            kind = KDPII_TO_KIND.get(p["label"])
            if kind is None:
                other.append(item)
            else:
                labels.append({"kind": kind, **item})
        rows.append(
            {
                "id": r["sent_idx"],
                "text": text,
                "labels": labels,
                "other": other,
                "difficulty": "kdpii",
            }
        )
    return rows


def name_sample(rows: list[dict], size: int, seed: int = NAME_SAMPLE_SEED) -> list[dict]:
    """이름 정답이 있는 문장은 전부 넣고, 나머지 자리는 이름 없는 문장에서 seed로 골라 섞는다."""
    named = [r for r in rows if any(lb["kind"] == "name" for lb in r["labels"])]
    if len(named) > size:
        raise ValueError(f"이름 문장 {len(named)}개가 표본 크기 {size}보다 많다")
    rest = [r for r in rows if not any(lb["kind"] == "name" for lb in r["labels"])]
    pick = named + random.Random(seed).sample(rest, size - len(named))
    random.Random(seed).shuffle(pick)
    return pick


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="KDPII를 받아 평가용 jsonl로 바꾼다")
    parser.add_argument("--split", choices=sorted(MD5), default="test")
    parser.add_argument("--raw", type=Path, help="이미 받은 {split}.json(없으면 Zenodo에서 받는다)")
    parser.add_argument(
        "--out", type=Path, help="출력 jsonl(기본 bench/datasets/external/kdpii_<split>.jsonl)"
    )
    parser.add_argument(
        "--name-sample",
        type=int,
        metavar="N",
        help="이름 문장 전부 + 나머지를 시드 458로 채운 N문장 표본도 <출력>_names<N>.jsonl로 쓴다",
    )
    args = parser.parse_args()

    if args.raw is not None:
        data = args.raw.read_bytes()
    else:
        with urllib.request.urlopen(RECORD_URL.format(split=args.split), timeout=120) as resp:
            data = read_capped(resp, SIZE[args.split])
    check_md5(data, args.split)
    rows = to_rows(json.loads(data.decode("utf-8")))

    out = args.out or OUT_DIR / f"kdpii_{args.split}.jsonl"
    write_jsonl(out, rows)
    n_labels = sum(len(r["labels"]) for r in rows)
    n_other = sum(len(r["other"]) for r in rows)
    print(f"{out}: {len(rows)}문장, 11종 정답 {n_labels}개, 범위 밖 라벨 {n_other}개")

    if args.name_sample:
        sample = name_sample(rows, args.name_sample)
        sample_out = out.with_name(f"{out.stem}_names{args.name_sample}.jsonl")
        write_jsonl(sample_out, sample)
        n_names = sum(lb["kind"] == "name" for r in sample for lb in r["labels"])
        print(f"{sample_out}: {len(sample)}문장, 이름 {n_names}개")


if __name__ == "__main__":
    main()
