# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII를 Zenodo에서 받아 평가용 jsonl로 바꾸는 CLI.

KDPII(한국어 대화 개인정보 데이터셋, https://doi.org/10.5281/zenodo.10968609, CC-BY-4.0)는 README의
이름 하이브리드 외부 비교와 대화 글 비교에 쓴다. 원자료와 변환본은 저장소에 싣지
않는다(SBOM 부록 D). 대신 누가 받아도 같은 파일이 되도록, 받은 파일의 MD5를 Zenodo에 적힌 값과
대조하고 한 줄에 한 문장씩 원본 순서대로 쓴다.

사용법:
    python -m bench.fetch_kdpii --split test
    python -m bench.fetch_kdpii --split test --raw test.json   # 이미 받은 파일을 바꾸기만 할 때
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

RECORD_URL = "https://zenodo.org/api/records/10968609/files/{split}.json/content"
# Zenodo 레코드 10968609에 적힌 파일별 MD5(2026-10-20 확인)
MD5 = {
    "train": "fa633403055e4e5918b92b2d11726434",
    "valid": "6f89923f873c840ca773d255d058150c",
    "test": "08eebd98593c1bad23fbf29053b3f9d2",
}
OUT_DIR = Path("bench/datasets/external")  # .gitignore에 있다


def check_md5(data: bytes, split: str) -> None:
    digest = hashlib.md5(data).hexdigest()
    if digest != MD5[split]:
        raise ValueError(f"{split}.json MD5가 Zenodo 값과 다르다: {digest} != {MD5[split]}")


def to_rows(records: list[dict]) -> list[dict]:
    """KDPII 문장 레코드를 {"id", "text", "entities"}로 바꾼다. 구간이 원문과 안 맞으면 멈춘다."""
    rows = []
    for r in records:
        text = r["sentence"]
        entities = []
        for p in r["PII_set"]:
            if text[p["begin"] : p["end"]] != p["form"]:
                raise ValueError(f"{r['sent_idx']}: 구간 {p['begin']}~{p['end']}이 원문과 다르다")
            entities.append({"start": p["begin"], "end": p["end"], "label": p["label"]})
        rows.append({"id": r["sent_idx"], "text": text, "entities": entities})
    return rows


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="KDPII를 받아 평가용 jsonl로 바꾼다")
    parser.add_argument("--split", choices=sorted(MD5), default="test")
    parser.add_argument("--raw", type=Path, help="이미 받은 {split}.json(없으면 Zenodo에서 받는다)")
    parser.add_argument("--out", type=Path, help=f"출력 jsonl(기본 {OUT_DIR}/kdpii_<split>.jsonl)")
    args = parser.parse_args()

    if args.raw is not None:
        data = args.raw.read_bytes()
    else:
        with urllib.request.urlopen(RECORD_URL.format(split=args.split), timeout=120) as resp:
            data = resp.read()
    check_md5(data, args.split)
    rows = to_rows(json.loads(data.decode("utf-8")))

    out = args.out or OUT_DIR / f"kdpii_{args.split}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{out}: {len(rows)}문장, 개인정보 {sum(len(r['entities']) for r in rows)}개")


if __name__ == "__main__":
    main()
