# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""파일 안전장치 테스트 — 합성 데이터만 사용.

MCP 도구는 AI 에이전트가 호출하므로, 여기 막아둔 것들이 실제로 막히는지 확인한다.
테스트 파일은 tmp_path(작업 디렉터리 밖)에 만들므로, 허용 루트를 tmp_path로 지정해 호출한다.
"""

import os
from pathlib import Path

import pytest

from maskingtape_mcp import safe_file
from maskingtape_mcp.safe_file import read_text_file, write_masked_copy

SYNTHETIC = "고객 연락처 010-1234-5678"
BS = chr(92)  # 백슬래시. 윈도 경로를 소스에 그대로 적지 않고 조립한다


@pytest.mark.parametrize(
    "path",
    [
        BS * 2 + "attacker" + BS + "share" + BS + "x.txt",  # UNC
        "//attacker/share/x.txt",  # 슬래시로 쓴 UNC
        "/" + BS + "attacker" + BS + "share" + BS + "x.txt",  # 구분자를 섞어 쓴 UNC
        BS * 2 + "?" + BS + "C:" + BS + "x.txt",  # 장치 경로
        BS * 2 + "." + BS + "PhysicalDrive0",  # 장치 경로
    ],
)
def test_rejects_network_and_device_paths_before_touching_the_filesystem(
    tmp_path, monkeypatch, path
):
    """UNC·장치 경로는 파일시스템을 건드리기 전에 문자열만 보고 거부한다(#494).

    is_symlink()·resolve()가 먼저 불리면 거부하기 전에 SMB 접속이 일어나고, 윈도에서는 이때
    로그인 인증 정보가 상대 서버로 나갈 수 있다.
    """

    def must_not_touch(*_args, **_kwargs):
        raise AssertionError("경로 검사 전에 파일시스템에 접근했다")

    # safe_file이 만드는 경로만 감시한다. pathlib 전체를 바꾸면 pytest 자신의 보고까지 깨진다.
    guarded = type(
        "GuardedPath",
        (type(Path()),),
        {name: must_not_touch for name in ("is_symlink", "resolve", "is_file", "stat", "exists")},
    )
    monkeypatch.setattr(safe_file, "Path", guarded)
    with pytest.raises(ValueError, match="네트워크"):
        read_text_file(path, root=tmp_path)


def test_default_root_refuses_a_drive_root(tmp_path, monkeypatch):
    """환경변수 없이 드라이브 루트에서 서버를 띄우면 경로 제한이 사라지므로 처리하지 않는다(#494)."""
    monkeypatch.delenv("MASKINGTAPE_MCP_ROOT", raising=False)
    monkeypatch.chdir(tmp_path.anchor)
    with pytest.raises(ValueError, match="MASKINGTAPE_MCP_ROOT"):
        read_text_file("문서.txt")


def test_default_root_refuses_the_home_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("MASKINGTAPE_MCP_ROOT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "문서.txt").write_text(SYNTHETIC, encoding="utf-8")
    with pytest.raises(ValueError, match="MASKINGTAPE_MCP_ROOT"):
        read_text_file("문서.txt")


def test_default_root_still_works_in_a_project_folder(tmp_path, monkeypatch):
    """평범한 작업 폴더에서는 환경변수 없이도 지금처럼 동작한다."""
    monkeypatch.delenv("MASKINGTAPE_MCP_ROOT", raising=False)
    project = tmp_path / "project"
    project.mkdir()
    (project / "문서.txt").write_text(SYNTHETIC, encoding="utf-8")
    monkeypatch.chdir(project)
    _, text = read_text_file("문서.txt")
    assert text == SYNTHETIC


def test_explicit_root_is_respected_even_at_a_drive_root(tmp_path, monkeypatch):
    """환경변수로 직접 정한 루트는 드라이브 루트여도 따른다(설정한 사람의 선택)."""
    monkeypatch.setenv("MASKINGTAPE_MCP_ROOT", tmp_path.anchor)
    (tmp_path / "문서.txt").write_text(SYNTHETIC, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    _, text = read_text_file(os.path.join(str(tmp_path), "문서.txt"))
    assert text == SYNTHETIC


def test_reads_a_normal_utf8_file(tmp_path):
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")

    path, text = read_text_file(str(src), root=tmp_path)

    assert path == src
    assert text == SYNTHETIC


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_text_file(str(tmp_path / "없는파일.txt"), root=tmp_path)


def test_rejects_non_utf8_file(tmp_path):
    src = tmp_path / "cp949.txt"
    src.write_bytes("주민번호 800101-1234560".encode("cp949"))
    with pytest.raises(ValueError, match="UTF-8"):
        read_text_file(str(src), root=tmp_path)


def test_rejects_file_over_the_size_limit(tmp_path):
    src = tmp_path / "큰파일.txt"
    src.write_text("가" * 100, encoding="utf-8")
    with pytest.raises(ValueError, match="너무 큽니다"):
        read_text_file(str(src), max_bytes=10, root=tmp_path)


def test_rejects_path_outside_root(tmp_path):
    """허용 루트 밖의 경로는 읽지 않는다 — 조작된 에이전트의 임의 파일 접근 차단."""
    outside = tmp_path / "outside.txt"
    outside.write_text(SYNTHETIC, encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    # 허용 루트를 workspace로 좁히면 그 밖의 outside.txt는 거부된다
    with pytest.raises(ValueError, match="작업 디렉터리 밖"):
        read_text_file(str(outside), root=workspace)


def test_rejects_parent_traversal_outside_root(tmp_path):
    """`..`로 루트를 벗어나려는 경로도 resolve() 정규화 후 거부된다."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text(SYNTHETIC, encoding="utf-8")
    sneaky = workspace / ".." / "secret.txt"  # 정규화하면 루트(workspace) 밖
    with pytest.raises(ValueError, match="작업 디렉터리 밖"):
        read_text_file(str(sneaky), root=workspace)


def test_rejects_symlink_input(tmp_path):
    """심볼릭 링크는 다른 위치(예: 개인 키)를 가리킬 수 있으므로 읽지 않는다."""
    secret = tmp_path / "secret.txt"
    secret.write_text("민감한 내용", encoding="utf-8")
    link = tmp_path / "겉보기문서.txt"
    try:
        link.symlink_to(secret)
    except OSError:  # Windows에서 개발자 모드/권한이 없으면 링크를 못 만든다
        pytest.skip("이 환경에서는 심볼릭 링크를 만들 수 없음")

    with pytest.raises(ValueError, match="심볼릭 링크"):
        read_text_file(str(link), root=tmp_path)


def test_writes_masked_copy_next_to_source(tmp_path):
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")

    dst = write_masked_copy(src, "마스킹된 내용", root=tmp_path)

    assert dst == tmp_path / "문서_masked.txt"
    assert dst.read_text(encoding="utf-8") == "마스킹된 내용"


def test_does_not_overwrite_an_existing_result_file(tmp_path):
    """이미 있는 결과 파일을 조용히 날리지 않는다 (사용자 데이터 보호)."""
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")
    existing = tmp_path / "문서_masked.txt"
    existing.write_text("먼저 있던 내용", encoding="utf-8")

    with pytest.raises(FileExistsError, match="덮어쓰지 않았습니다"):
        write_masked_copy(src, "새 내용", root=tmp_path)

    assert existing.read_text(encoding="utf-8") == "먼저 있던 내용"  # 원본 그대로


def test_rejects_symlinked_output_path(tmp_path):
    """결과 경로가 링크면 링크 대상 파일을 덮어쓸 수 있으므로 거부한다."""
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")
    victim = tmp_path / "중요파일.txt"
    victim.write_text("덮어쓰이면 안 되는 내용", encoding="utf-8")
    link = tmp_path / "문서_masked.txt"
    try:
        link.symlink_to(victim)
    except OSError:
        pytest.skip("이 환경에서는 심볼릭 링크를 만들 수 없음")

    with pytest.raises(ValueError, match="심볼릭 링크"):
        write_masked_copy(src, "새 내용", root=tmp_path)

    assert victim.read_text(encoding="utf-8") == "덮어쓰이면 안 되는 내용"
