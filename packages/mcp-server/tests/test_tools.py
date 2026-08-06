"""MCP 도구 함수 테스트 — MCP 런타임 없이 순수 함수만 검증한다. 합성 데이터만 사용."""

import pytest

from maskingtape_mcp import tools

SYNTHETIC = "고객 연락처 010-1234-5678, 주민번호 800101-1234560"
# 같은 번호가 두 번 등장 — numbered 라벨이 같은 번호로 묶이는지 확인용
REPEATED = "김철수 010-1234-5678, 김철수 010-1234-5678"


@pytest.fixture(autouse=True)
def _reset_llm_mode():
    """LLM 모드는 전역 상태라, 각 테스트 후 규칙 전용으로 되돌려 다른 테스트를 오염시키지 않는다."""
    yield
    tools.set_llm_mode(False)


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


def test_default_mode_is_rule_only_without_ollama():
    # 기본은 규칙 전용(Ollama 불필요 안전 바닥) — _detectors()가 None이면 Pipeline이 규칙 기본을 쓴다
    assert tools._detectors() is None
    report = tools.scan_text("연락처 010-1234-5678")
    assert any(d["kind"] == "phone" for d in report)


def test_llm_mode_uses_llm_detectors():
    # --llm이 켜지면 탐지기 세트에 LLM 이름 탐지기가 들어간다
    from maskingtape.detectors import LLMNameDetector

    tools.set_llm_mode(True)
    assert any(isinstance(d, LLMNameDetector) for d in tools._detectors())


def test_server_llm_flag_enables_llm_mode(monkeypatch):
    # server.main()이 --llm을 파싱해 LLM 모드를 켠다 (mcp.run은 막아 실제 서버는 안 띄운다)
    from maskingtape_mcp import server

    monkeypatch.setattr("sys.argv", ["maskingtape-mcp", "--llm"])
    monkeypatch.setattr(server.mcp, "run", lambda: None)
    server.main()
    assert tools._detectors() is not None


def test_server_without_flag_keeps_rule_mode(monkeypatch):
    from maskingtape_mcp import server

    monkeypatch.setattr("sys.argv", ["maskingtape-mcp"])
    monkeypatch.setattr(server.mcp, "run", lambda: None)
    server.main()
    assert tools._detectors() is None
