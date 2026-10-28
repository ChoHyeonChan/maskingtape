# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""Table parsing must preserve source spans without rescanning escaped CSV fields."""

import csv
from statistics import median
from time import perf_counter

import pytest

from maskingtape.detectors import NameDetector


def test_escaped_csv_fields_scale_linearly():
    detector = NameDetector()
    texts = {n: ",".join(['"a""b"'] * n) for n in (4000, 8000)}
    timings: dict[int, list[float]] = {n: [] for n in texts}
    detector.detect(",".join(['"a""b"'] * 100))

    for _ in range(3):
        for n, text in texts.items():
            start = perf_counter()
            found = detector.detect(text)
            timings[n].append(perf_counter() - start)
            assert found == []

    small, large = (median(timings[n]) for n in texts)
    assert large < 3 * small + 0.01, (small, large, large / small)


def test_strong_and_weak_header_checks_share_parsed_cells(monkeypatch):
    calls = []
    parse = NameDetector._table_cells

    def counted(line, sep):
        calls.append((line, sep))
        return parse(line, sep)

    monkeypatch.setattr(NameDetector, "_table_cells", staticmethod(counted))
    text = ','.join(['"a""b"'] * 10)

    assert NameDetector().detect(text) == []
    assert calls == [(text, ",")]


@pytest.mark.parametrize("sep", [",", "\t", "|", "/"])
@pytest.mark.parametrize(
    "fields",
    [
        ['"a""b"', '" 김민수 "', '"a""b"', '"이서연"'],
        ['"a,b"', '"김민수"', '""', " 이서연 "],
        ['""""', "김민수", "", "이서연"],
        ['a"b', "김민수", '"a"b', "이서연"],
    ],
)
def test_table_cells_keep_name_spans_after_escaped_fields(sep, fields):
    line = sep.join(fields)
    cells = NameDetector._table_cells(line, sep)

    assert cells is not None
    assert [value for value, _, _ in cells] == [
        value.strip() for value in next(csv.reader([line], delimiter=sep))
    ]
    for value, start, end in cells:
        if value in {"김민수", "이서연"}:
            assert line[start:end] == value


def test_csv_name_column_keeps_source_span_after_escaped_field():
    text = '메모,성명,비고\n"a""b","탁서윤","a,b"\n"c""d","류하은","e""f"'
    found = NameDetector().detect(text)

    assert [d.text for d in found] == ["탁서윤", "류하은"]
    assert all(text[d.start:d.end] == d.text for d in found)
