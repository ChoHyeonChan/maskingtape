"""MCP 도구 함수 테스트 — MCP 런타임 없이 순수 함수만 검증한다. 합성 데이터만 사용."""

import pytest

from maskingtape_mcp import tools

SYNTHETIC = "고객 연락처 010-1234-5678, 주민번호 800101-1234560"


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


def test_server_module_registers_tools():
    # 서버 모듈이 임포트되고 FastMCP 인스턴스가 구성되는지 확인 (실행은 안 함)
    from maskingtape_mcp import server

    assert server.mcp.name == "maskingtape"
