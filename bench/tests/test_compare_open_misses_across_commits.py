# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""compare_open_misses_across_commits.py의 표 만들기 검증.

두 커밋을 실제로 설치해 재는 부분(가상환경 두 개 생성)은 느리고 네트워크가 필요해서 여기서
돌리지 않는다. 채점 결과 JSON을 표로 바꾸는 부분만 확인한다.
"""

from __future__ import annotations

from bench.evaluators.compare_open_misses_across_commits import (
    _EVALUATE_OPEN_MISSES_SCRIPT,
    format_comparison_table,
)


def _result(recalls: dict[tuple[int, str], float], total_fp: int = 0) -> dict:
    return {
        "per_tag": [{"issue": issue, "tag": tag, "recall": r} for (issue, tag), r in recalls.items()],
        "total_fp": total_fp,
    }


def test_table_marks_regressions_and_improvements():
    result = {
        "before": _result({(600, "name_unlisted_ending"): 1.0, (601, "two"): 0.0, (602, "list"): 0.5}),
        "after": _result({(600, "name_unlisted_ending"): 0.0, (601, "two"): 1.0, (602, "list"): 0.5}, total_fp=2),
    }
    lines = format_comparison_table(result, "old", "new").splitlines()
    by_tag = {line.split()[1]: line for line in lines if line.startswith("#")}
    assert by_tag["name_unlisted_ending"].endswith("▼")  # 잡히던 게 새기 시작했다
    assert by_tag["two"].endswith("▲")  # 못 잡던 걸 잡게 됐다
    assert not by_tag["list"].endswith(("▲", "▼"))
    assert "old 0건 → new 2건" in lines[-1]


def test_tag_missing_on_one_side_is_shown_as_zero():
    """옛 커밋에 없던 태그(세트에 나중에 넣은 모양)도 표에서 빠지지 않는다."""
    result = {"before": _result({}), "after": _result({(593, "building"): 1.0})}
    table = format_comparison_table(result, "old", "new")
    assert "#593" in table and "0.000" in table and "1.000" in table


def test_scoring_script_exists_and_is_standalone():
    """임시 가상환경에는 bench가 설치되지 않는다 — 채점 스크립트가 bench를 import하면 거기서 깨진다."""
    source = _EVALUATE_OPEN_MISSES_SCRIPT.read_text(encoding="utf-8")
    assert "from bench" not in source and "import bench" not in source
