"""파일 안전장치 테스트 — 합성 데이터만 사용.

MCP 도구는 AI 에이전트가 호출하므로, 여기 막아둔 것들이 실제로 막히는지 확인한다.
"""

import pytest

from maskingtape_mcp.safe_file import read_text_file, write_masked_copy

SYNTHETIC = "고객 연락처 010-1234-5678"


def test_reads_a_normal_utf8_file(tmp_path):
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")

    path, text = read_text_file(str(src))

    assert path == src
    assert text == SYNTHETIC


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_text_file(str(tmp_path / "없는파일.txt"))


def test_rejects_non_utf8_file(tmp_path):
    src = tmp_path / "cp949.txt"
    src.write_bytes("주민번호 800101-1234560".encode("cp949"))
    with pytest.raises(ValueError, match="UTF-8"):
        read_text_file(str(src))


def test_rejects_file_over_the_size_limit(tmp_path):
    src = tmp_path / "큰파일.txt"
    src.write_text("가" * 100, encoding="utf-8")
    with pytest.raises(ValueError, match="너무 큽니다"):
        read_text_file(str(src), max_bytes=10)


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
        read_text_file(str(link))


def test_writes_masked_copy_next_to_source(tmp_path):
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")

    dst = write_masked_copy(src, "마스킹된 내용")

    assert dst == tmp_path / "문서_masked.txt"
    assert dst.read_text(encoding="utf-8") == "마스킹된 내용"


def test_does_not_overwrite_an_existing_result_file(tmp_path):
    """이미 있는 결과 파일을 조용히 날리지 않는다 (사용자 데이터 보호)."""
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")
    existing = tmp_path / "문서_masked.txt"
    existing.write_text("먼저 있던 내용", encoding="utf-8")

    with pytest.raises(FileExistsError, match="덮어쓰지 않았습니다"):
        write_masked_copy(src, "새 내용")

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
        write_masked_copy(src, "새 내용")

    assert victim.read_text(encoding="utf-8") == "덮어쓰이면 안 되는 내용"
