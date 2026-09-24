# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""데이터셋 생성 CLI(generate_dataset.py)와 커밋된 데이터셋의 재현성 검증(#431).

제출 보고서·README의 정확도 수치는 `bench/datasets/synth_v1.jsonl`이 근거라, 이 파일이 기본 옵션 + 시드만으로
다시 만들어지는지가 곧 그 수치의 신뢰도다. 생성기를 고치다 난수 흐름이 바뀌면(새 템플릿·새 표기 추가 등)
조용히 어긋나기 쉬워서 CI가 잡게 한다. 의도한 변경이면 새 옵션 뒤로 옮기거나(v2처럼) v1을 일부러 다시
만들고 수치를 갱신한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from bench.generate_dataset import V1_DATASET_NAME, build_dataset, main
from bench.generator.address_shapes import SHAPE_MARKERS

_DATASETS = Path(__file__).resolve().parents[1] / "datasets"
_COUNT, _SEED = 500, 42


def _load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _address_texts(rows: list[dict]) -> list[str]:
    return [r["text"][lb["start"] : lb["end"]] for r in rows for lb in r["labels"] if lb["kind"] == "address"]


def test_committed_v1_dataset_is_reproducible_from_seed():
    """기본 옵션 + 시드 42로 다시 만들면 커밋된 synth_v1.jsonl과 같다(파싱 비교라 줄바꿈 차이에 안 흔들린다)."""
    expected = _load_rows(_DATASETS / V1_DATASET_NAME)
    assert build_dataset(_COUNT, _SEED) == expected, (
        "synth_v1.jsonl을 시드로 재생성할 수 없다 — 생성기 변경이 난수 흐름을 바꿨다. "
        "새 표기를 넣는 변경이면 v2처럼 옵션 뒤로 옮기고, v1을 일부러 갱신하는 거면 수치를 함께 갱신한다."
    )


def test_committed_v2_dataset_is_reproducible_from_seed():
    expected = _load_rows(_DATASETS / "synth_v2.jsonl")
    assert build_dataset(_COUNT, _SEED, address_extended=True) == expected


def test_v1_has_no_extended_address_shapes_but_v2_has_all_of_them():
    """이슈 #431의 전제 — v1엔 #423이 고친 형태가 한 건도 없어 그 경계가 주소 F1 1.000 뒤에 숨는다."""
    v1 = _address_texts(_load_rows(_DATASETS / V1_DATASET_NAME))
    v2 = _address_texts(_load_rows(_DATASETS / "synth_v2.jsonl"))
    for name, marker in SHAPE_MARKERS.items():
        assert not any(marker.search(t) for t in v1), f"v1에 {name} 형태가 있다"
        assert sum(1 for t in v2 if marker.search(t)) >= 2, f"v2에 {name} 형태가 2건 미만"


def test_v2_includes_county_addresses_without_province():
    """시/도 없이 군으로 시작하는 표기("양평군 양평읍 ...")도 v2에 들어 있다 — 이슈 #431의 `_NO_PROVINCE_AREAS` 항목."""
    v2 = _address_texts(_load_rows(_DATASETS / "synth_v2.jsonl"))
    county = [t for t in v2 if SHAPE_MARKERS["county_road"].search(t) or SHAPE_MARKERS["county_ri"].search(t)]
    assert any(t.split()[0].endswith("군") for t in county), "v2에 시/도 없는 군 지역 주소가 없다"
    assert any(not t.split()[0].endswith("군") for t in county), "v2에 시/도 있는 군 지역 주소가 없다"


def test_address_extended_refuses_to_overwrite_v1(tmp_path, monkeypatch):
    """--address-extended는 v1과 다른 데이터셋을 만든다 — v1 파일명으로 저장하려 하면 막는다.

    임시 폴더에 v1과 같은 이름의 파일을 두고 시도한다(가드가 깨져도 진짜 v1은 건드리지 않게).
    """
    target = tmp_path / V1_DATASET_NAME
    target.write_text("keep\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["generate_dataset", "--address-extended", "--out", str(target)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_address_extended_writes_a_new_file(tmp_path, monkeypatch):
    target = tmp_path / "synth_v2_small.jsonl"
    monkeypatch.setattr(
        sys, "argv", ["generate_dataset", "--count", "30", "--seed", "1", "--address-extended", "--out", str(target)]
    )
    main()
    rows = _load_rows(target)
    assert len(rows) == 30
    assert rows == build_dataset(30, 1, address_extended=True)
