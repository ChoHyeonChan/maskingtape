# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII 받기·변환 CLI(bench/fetch_kdpii.py). 네트워크 없이 합성 레코드로만 본다."""

import hashlib
import io
from pathlib import Path

import pytest

from bench import fetch_kdpii


def _pii(text: str, form: str, label: str) -> dict:
    begin = text.index(form)
    return {"form": form, "label": label, "begin": begin, "end": begin + len(form)}


TEXT = "김민수 씨 번호는 010-1234-5678이에요. 직장은 한빛상사예요."
RECORD = {
    "sent_idx": "Data0.1_1_0",
    "sentence": TEXT,
    "PII_set": [
        _pii(TEXT, "김민수", "PS_NAME"),
        _pii(TEXT, "010-1234-5678", "QT_MOBILE"),
        _pii(TEXT, "한빛상사", "OG_WORKPLACE"),
    ],
}


def _row(idx: int, labels: list[dict]) -> dict:
    return {"id": f"s{idx}", "text": "가", "labels": labels, "other": [], "difficulty": "kdpii"}


def test_to_rows_splits_mapped_labels_and_other() -> None:
    rows = fetch_kdpii.to_rows(
        [RECORD, {"sent_idx": "Data0.1_2_1", "sentence": "네.", "PII_set": []}]
    )
    assert [r["id"] for r in rows] == ["Data0.1_1_0", "Data0.1_2_1"]
    assert rows[0]["text"] == TEXT
    assert rows[0]["labels"] == [
        {"kind": "name", "start": 0, "end": 3, "raw": "PS_NAME"},
        {"kind": "phone", "start": 10, "end": 23, "raw": "QT_MOBILE"},
    ]
    start = TEXT.index("한빛상사")
    assert rows[0]["other"] == [{"start": start, "end": start + 4, "raw": "OG_WORKPLACE"}]
    assert rows[0]["difficulty"] == "kdpii"
    assert rows[1]["labels"] == [] and rows[1]["other"] == []


def test_to_rows_maps_phone_and_rrn_variants_to_one_kind() -> None:
    assert (
        fetch_kdpii.KDPII_TO_KIND["QT_PHONE"] == fetch_kdpii.KDPII_TO_KIND["QT_MOBILE"] == "phone"
    )
    assert (
        fetch_kdpii.KDPII_TO_KIND["QT_RESIDENT_NUMBER"]
        == fetch_kdpii.KDPII_TO_KIND["QT_ALIEN_NUMBER"]
        == "rrn"
    )
    assert "biz_reg" not in fetch_kdpii.KDPII_TO_KIND.values()


def test_to_rows_rejects_span_that_does_not_match_text() -> None:
    bad = dict(
        RECORD, PII_set=[{"id": 0, "form": "이서연", "label": "PS_NAME", "begin": 0, "end": 3}]
    )
    with pytest.raises(ValueError):
        fetch_kdpii.to_rows([bad])


def test_name_sample_keeps_every_named_row_and_is_deterministic() -> None:
    name = {"kind": "name", "start": 0, "end": 1, "raw": "PS_NAME"}
    phone = {"kind": "phone", "start": 0, "end": 1, "raw": "QT_MOBILE"}
    rows = [_row(i, [name] if i % 10 == 0 else ([phone] if i % 3 == 0 else [])) for i in range(100)]
    a = fetch_kdpii.name_sample(rows, 30)
    b = fetch_kdpii.name_sample(rows, 30)
    assert a == b
    assert len(a) == 30 and len({r["id"] for r in a}) == 30
    named = {r["id"] for r in rows if r["labels"] == [name]}
    assert named <= {r["id"] for r in a}
    assert [r["id"] for r in a] != sorted((r["id"] for r in a), key=lambda s: int(s[1:]))  # 섞였다
    with pytest.raises(ValueError):
        fetch_kdpii.name_sample(rows, 5)


def test_check_md5_rejects_changed_file(monkeypatch: pytest.MonkeyPatch) -> None:
    data = b"[]"
    monkeypatch.setitem(fetch_kdpii.MD5, "test", hashlib.md5(data).hexdigest())
    monkeypatch.setitem(fetch_kdpii.SIZE, "test", len(data))
    fetch_kdpii.check_md5(data, "test")
    with pytest.raises(ValueError, match="MD5"):
        fetch_kdpii.check_md5(b"{}", "test")
    with pytest.raises(ValueError, match="크기"):
        fetch_kdpii.check_md5(b"[ ]", "test")


def test_read_capped_reads_everything_but_stops_past_limit() -> None:
    data = b"x" * ((1 << 20) * 2 + 5)
    assert fetch_kdpii.read_capped(io.BytesIO(data), len(data)) == data
    with pytest.raises(ValueError):
        fetch_kdpii.read_capped(io.BytesIO(data), len(data) - 1)


def test_default_output_is_inside_bench_regardless_of_cwd() -> None:
    assert (
        fetch_kdpii.OUT_DIR == Path(fetch_kdpii.__file__).resolve().parent / "datasets" / "external"
    )
