# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""라이선스 헤더 검사 스크립트 테스트. scripts/는 패키지가 아니라 경로로 불러온다."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_license_headers", Path(__file__).resolve().parents[1] / "check_license_headers.py"
)
chk = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(chk)


@pytest.mark.parametrize("suffix", sorted(chk.COMMENT_STYLE))
def test_expected_header_is_accepted_by_the_checker(suffix):
    # 안내로 보여 주는 헤더를 그대로 붙이면 검사를 통과해야 한다
    assert chk.has_header(chk.expected_header(suffix) + "\n\nbody\n")


def test_header_may_follow_a_shebang_or_doctype():
    assert chk.has_header("#!/usr/bin/env python\n" + chk.expected_header(".py") + "\n")
    assert chk.has_header("<!doctype html>\n" + chk.expected_header(".html") + "\n<html>\n")


def test_missing_copyright_or_license_line_fails():
    assert not chk.has_header("# SPDX-License-Identifier: Apache-2.0\n\nimport os\n")
    assert not chk.has_header("# SPDX-FileCopyrightText: 2026 The maskingtape Authors\n\nimport os\n")
    assert not chk.has_header("import os\n")
    assert not chk.has_header("")


def test_other_license_does_not_count():
    # 다른 라이선스 식별자는 우리 파일로 보지 않는다 — 복사해 온 코드가 섞였다는 신호다
    text = "# SPDX-FileCopyrightText: 2026 The maskingtape Authors\n# SPDX-License-Identifier: MIT\n"
    assert not chk.has_header(text)


def test_header_below_the_first_lines_fails():
    text = "\n" * chk.HEAD_LINES + chk.expected_header(".py") + "\n"
    assert not chk.has_header(text)


def test_target_selection():
    assert chk.is_target("packages/core/maskingtape/cli.py")
    assert chk.is_target("apps/web/src/App.tsx")
    assert chk.is_target("apps/web/index.html")
    assert not chk.is_target("apps/desktop/windows/runner/main.cpp")
    assert not chk.is_target("apps/desktop/windows/runner/fake.dart")  # 생성 파일 폴더는 확장자와 무관하게 제외
    assert not chk.is_target("README.md")
    assert not chk.is_target("apps/web/package.json")


def test_find_missing_reports_only_tracked_files_without_header(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "good.py").write_text(chk.expected_header(".py") + "\n", encoding="utf-8")
    (tmp_path / "bad.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("헤더가 필요 없는 문서\n", encoding="utf-8")
    (tmp_path / "untracked.py").write_text("import os\n", encoding="utf-8")
    subprocess.run(["git", "add", "good.py", "bad.ts", "notes.md"], cwd=tmp_path, check=True)

    assert chk.find_missing(tmp_path) == ["bad.ts"]


def test_repository_files_all_have_headers():
    # 저장소 자체가 규칙을 지키는지 — CI 단계와 같은 검사를 테스트로도 고정한다
    assert chk.find_missing(chk.REPO_ROOT) == []
