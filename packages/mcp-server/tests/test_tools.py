"""MCP 도구 함수 테스트 — MCP 런타임 없이 순수 함수만 검증한다. 합성 데이터만 사용."""

import pytest

from maskingtape_mcp import tools

SYNTHETIC = "고객 연락처 010-1234-5678, 주민번호 800101-1234560"
# 같은 번호가 두 번 등장 — numbered 라벨이 같은 번호로 묶이는지 확인용
REPEATED = "김철수 010-1234-5678, 김철수 010-1234-5678"


def test_scan_text_reports_detections():
    report = tools.scan_text(SYNTHETIC)
    kinds = {d["kind"] for d in report}
    assert {"phone", "rrn"} <= kinds


def test_anonymize_text_mask():
    out = tools.anonymize_text(SYNTHETIC)
    assert "010-1234-5678" not in out
    assert "800101-1234560" not in out


def test_anonymize_text_label():
    out = tools.anonymize_text(SYNTHETIC, strategy="label")
    assert "[전화번호]" in out
    assert "[주민등록번호]" in out


def test_anonymize_text_rejects_unknown_strategy():
    with pytest.raises(ValueError):
        tools.anonymize_text(SYNTHETIC, strategy="rot13")


def test_anonymize_text_numbered_labels_same_value_consistently():
    out = tools.anonymize_text(REPEATED, strategy="label", numbered=True)
    # 같은 값은 같은 번호를 받으므로 [전화번호1]이 두 번 나오고 [전화번호2]는 없다
    assert out.count("[전화번호1]") == 2
    assert "[전화번호2]" not in out


def test_anonymize_file_writes_masked_copy_and_reports(tmp_path):
    src = tmp_path / "문서.txt"
    src.write_text(SYNTHETIC, encoding="utf-8")

    report = tools.anonymize_file(str(src))

    dst = tmp_path / "문서_masked.txt"
    assert dst.exists()
    masked = dst.read_text(encoding="utf-8")
    assert "010-1234-5678" not in masked
    assert "800101-1234560" not in masked
    assert report["output"] == str(dst)
    assert report["detections"] == 2
    assert report["by_kind"] == {"phone": 1, "rrn": 1}


def test_anonymize_file_missing_path_raises():
    with pytest.raises(FileNotFoundError):
        tools.anonymize_file("존재하지_않는_파일.txt")


def test_anonymize_file_rejects_non_utf8(tmp_path):
    src = tmp_path / "cp949.txt"
    src.write_bytes("주민번호 800101-1234560".encode("cp949"))
    with pytest.raises(ValueError):
        tools.anonymize_file(str(src))


def test_server_module_registers_tools():
    # 서버 모듈이 임포트되고 FastMCP 인스턴스가 구성되는지 확인 (실행은 안 함)
    from maskingtape_mcp import server

    assert server.mcp.name == "maskingtape"
