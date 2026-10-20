# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII 받기·변환 CLI(bench/fetch_kdpii.py). 네트워크 없이 합성 레코드로만 본다."""

import hashlib

import pytest

from bench import fetch_kdpii

RECORD = {
    "sent_idx": "Data0.1_1_0",
    "sentence": "김민수 씨 번호는 010-1234-5678이에요.",
    "PII_set": [
        {"id": 0, "form": "김민수", "label": "PS_NAME", "begin": 0, "end": 3},
        {"id": 1, "form": "010-1234-5678", "label": "QT_MOBILE", "begin": 10, "end": 23},
    ],
}


def test_to_rows_keeps_order_text_and_spans() -> None:
    rows = fetch_kdpii.to_rows([RECORD, {"sent_idx": "Data0.1_2_1", "sentence": "네.", "PII_set": []}])
    assert [r["id"] for r in rows] == ["Data0.1_1_0", "Data0.1_2_1"]
    assert rows[0]["text"] == RECORD["sentence"]
    assert rows[0]["entities"] == [
        {"start": 0, "end": 3, "label": "PS_NAME"},
        {"start": 10, "end": 23, "label": "QT_MOBILE"},
    ]
    assert rows[1]["entities"] == []


def test_to_rows_rejects_span_that_does_not_match_text() -> None:
    bad = dict(RECORD, PII_set=[{"id": 0, "form": "이서연", "label": "PS_NAME", "begin": 0, "end": 3}])
    with pytest.raises(ValueError):
        fetch_kdpii.to_rows([bad])


def test_check_md5_rejects_changed_file(monkeypatch: pytest.MonkeyPatch) -> None:
    data = b"[]"
    monkeypatch.setitem(fetch_kdpii.MD5, "test", hashlib.md5(data).hexdigest())
    fetch_kdpii.check_md5(data, "test")
    with pytest.raises(ValueError):
        fetch_kdpii.check_md5(b"[ ]", "test")
