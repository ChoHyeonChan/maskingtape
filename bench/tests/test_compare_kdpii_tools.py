# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""KDPII 타 도구 비교 채점(bench/evaluators/compare_kdpii_tools.py)과 어댑터. 합성 문장만 쓴다.

ko-pii·Presidio는 CI에 없으므로 가짜 도구로 채점·리포트 경로를 보고, 실제 도구 결과는 bench README의
수치(비교용 가상환경에서 잰 값)로 남긴다.
"""

from pathlib import Path

import pytest

from bench.evaluators import compare_kdpii_tools as cmp
from bench.evaluators import pii_tool_adapters as adapters


def _span(text: str, part: str, kind: str | None = None) -> dict:
    start = text.index(part)
    out = {"start": start, "end": start + len(part)}
    if kind is not None:
        out["kind"] = kind
    return out


def _pred(text: str, part: str, kind: str | None, label: str = "X") -> dict:
    return {"label": label, **_span(text, part), "kind": kind}


def _covered(text: str, *parts: str) -> list[bool]:
    covered = [False] * len(text)
    for part in parts:
        s = _span(text, part)
        for i in range(s["start"], s["end"]):
            covered[i] = True
    return covered


def test_number_label_counts_as_masked_when_only_digits_are_covered() -> None:
    text = "우리은행 1002-123-456789로 보내 주세요"
    gold = _span(text, "우리은행 1002-123-456789", "account")
    assert cmp.mask_state(text, _covered(text, "1002-123-456789"), gold) == "full"
    assert cmp.mask_state(text, _covered(text, "1002-123"), gold) == "partial"
    assert cmp.mask_state(text, _covered(text), gold) == "none"


def test_other_labels_need_every_non_space_character() -> None:
    text = "김민수 씨는 서울 중구에 산다"
    name = _span(text, "김민수", "name")
    assert cmp.mask_state(text, _covered(text, "김민"), name) == "partial"
    assert cmp.mask_state(text, _covered(text, "김민수"), name) == "full"
    address = _span(text, "서울 중구", "address")
    assert cmp.mask_state(text, _covered(text, "서울", "중구"), address) == "full"


def test_score_counts_masking_stray_detections_and_negative_sentences() -> None:
    t1, t2, t3, t4 = (
        "김민수 씨 010-1234-5678",
        "직장은 한빛상사예요",
        "오늘 날씨 좋네요",
        "네 알겠습니다",
    )
    rows = [
        {
            "text": t1,
            "labels": [_span(t1, "김민수", "name"), _span(t1, "010-1234-5678", "phone")],
            "other": [],
        },
        {"text": t2, "labels": [], "other": [_span(t2, "한빛상사")]},
        {"text": t3, "labels": [], "other": []},
        {"text": t4, "labels": [], "other": []},
    ]
    preds = [
        [_pred(t1, "김민수", "name"), _pred(t1, "010-1234-5678", "phone")],
        [_pred(t2, "한빛상사", None, "ORG")],  # 범위 밖 라벨과 겹친다 → 엉뚱한 곳이 아니다
        [_pred(t3, "오늘", "birth_date", "DATE_TIME")],  # 아무것과도 안 겹친다
        [],
    ]
    r = cmp.score(rows, preds)
    assert (r["n_gold"], r["full"], r["partial"], r["none"]) == (2, 2, 0, 0)
    assert r["stray"] == 1 and r["n_pred"] == 4
    assert r["neg_docs"] == [1, 2]
    assert r["all_labels"] == [3, 3]
    assert r["exact"][0] == pytest.approx(2 / 3) and r["exact"][1] == 1.0
    assert r["mask_kind"] == {"name": [1, 1], "phone": [1, 1]}


def test_unmapped_detection_masks_but_does_not_count_as_typed_match() -> None:
    text = "김민수"
    rows = [{"text": text, "labels": [_span(text, "김민수", "name")], "other": []}]
    r = cmp.score(rows, [[_pred(text, "김민수", None, "NICKNAME")]])
    assert r["full"] == 1
    assert r["exact"][1] == 0.0 and r["overlap"][1] == 0.0


def test_overlap_matches_shifted_span_but_exact_does_not() -> None:
    text = "김민수님께 전화"
    rows = [{"text": text, "labels": [_span(text, "김민수", "name")], "other": []}]
    r = cmp.score(rows, [[_pred(text, "김민수님", "name")]])
    assert r["exact"][1] == 0.0
    assert r["overlap"][1] == 1.0


def test_score_rejects_prediction_count_mismatch() -> None:
    with pytest.raises(ValueError):
        cmp.score([{"text": "네", "labels": []}], [])


def test_report_lists_every_tool_with_counts(tmp_path: Path) -> None:
    text = "김민수 씨 010-1234-5678"
    rows = [
        {
            "text": text,
            "labels": [_span(text, "김민수", "name"), _span(text, "010-1234-5678", "phone")],
        }
    ]
    tools = [
        adapters.Tool(
            "all",
            {"fake": "1"},
            lambda t: [_pred(t, "김민수", "name"), _pred(t, "010-1234-5678", "phone")],
        ),
        adapters.Tool("none", {"fake": "1"}, lambda t: []),
    ]
    results = {}
    for tool in tools:
        preds, ms = cmp.run_tool(tool, rows)
        results[tool.name] = {**cmp.score(rows, preds), "ms_per_doc": ms}
    report = cmp.format_report(tmp_path / "kdpii_test.jsonl", rows, tools, results)
    assert (
        "`kdpii_test.jsonl`" in report and tmp_path.name not in report
    )  # 절대 경로(사용자 이름)를 싣지 않는다
    assert "| all | 2 (1.000) | 0 | 0 | 0/2 |" in report
    assert "| none | 0 (0.000) | 0 | 2 | 0/0 |" in report
    assert "| name | 1 | 1 · 1.000 | 0 · 0.000 |" in report


def test_maskingtape_adapter_returns_kind_as_label() -> None:
    tool = adapters.maskingtape_rules()
    found = tool.predict("연락처는 010-1234-5678입니다")
    assert {"label": "phone", "kind": "phone", "start": 5, "end": 18} in found


def test_unmapped_tool_label_keeps_none_kind() -> None:
    assert adapters.to_pred("PERSON", adapters.PRESIDIO_TO_KIND, 0, 3)["kind"] == "name"
    assert adapters.to_pred("NRP", adapters.PRESIDIO_TO_KIND, 0, 3)["kind"] is None
    assert adapters.to_pred("DT_BIRTH", adapters.KOPII_TO_KIND, 0, 3)["kind"] == "birth_date"


def test_unknown_tool_and_missing_package_fail_with_clear_errors() -> None:
    with pytest.raises(ValueError):
        adapters.build_tools(["scrubadub"])
    with pytest.raises(RuntimeError, match="비교용 가상환경"):
        adapters._require("maskingtape_no_such_module", "없는-패키지")
