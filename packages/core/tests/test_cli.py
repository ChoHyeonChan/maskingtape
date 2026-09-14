# SPDX-License-Identifier: Apache-2.0

"""CLI 통합 테스트 — 표준입출력 인코딩까지 검증하므로 실제 프로세스를 띄운다.

여기 쓰는 개인정보는 전부 합성(가짜)이다. 주민등록번호는 체크섬만 맞춘 값이다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error

from maskingtape import cli
from maskingtape.detectors.personal import name_llm

SAMPLE = "고객 김철수 주민번호 800101-1234560 연락처 010-1234-5678"


def run_cli(*args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    """CLI를 별도 프로세스로 실행한다.

    PYTHONIOENCODING을 지우고 실행한다 — 이 변수가 설정돼 있으면 콘솔 기본 인코딩 문제가
    가려져 정작 검증하려는 회귀를 놓친다(새 환경 검증에서 실제로 그랬다).
    """
    env = {key: value for key, value in os.environ.items() if key != "PYTHONIOENCODING"}
    return subprocess.run(
        [sys.executable, "-m", "maskingtape.cli", *args],
        input=stdin,
        capture_output=True,
        check=False,
        env=env,
    )


def test_masks_name_from_piped_utf8_input():
    """파이프로 넣은 UTF-8 문서도 인자로 줄 때와 똑같이 마스킹돼야 한다.

    콘솔 기본 인코딩(Windows에서 cp949)으로 읽으면 한글이 깨져 이름·주소 탐지가 실패한다.
    숫자는 ASCII라 살아남기 때문에 '동작하는 것처럼 보이면서 이름만 유출'된다.
    """
    result = run_cli(stdin=SAMPLE.encode("utf-8"))
    assert result.returncode == 0
    output = result.stdout.decode("utf-8")
    assert "김철수" not in output
    assert "800101-1234560" not in output


def test_piped_and_argument_input_produce_the_same_output():
    argument = run_cli(SAMPLE)
    piped = run_cli(stdin=SAMPLE.encode("utf-8"))
    assert argument.stdout.decode("utf-8").strip() == piped.stdout.decode("utf-8").strip()


def test_does_not_crash_on_characters_outside_the_console_codepage():
    """이모지가 섞여도 죽지 않는다 — 한국어 채팅·리뷰 데이터에는 흔하다."""
    result = run_cli("고객 😀 주민번호 800101-1234560 문의")
    assert result.returncode == 0
    output = result.stdout.decode("utf-8")
    assert "😀" in output
    assert "800101-1234560" not in output


def test_output_is_utf8_when_redirected():
    """리다이렉트한 결과가 UTF-8이어야 다음 단계(파일·파이프)가 깨지지 않는다."""
    result = run_cli(SAMPLE)
    assert "김철수" not in result.stdout.decode("utf-8")  # 디코딩 실패 시 예외로 드러난다


def test_rejects_input_that_is_not_utf8():
    """UTF-8로 읽을 수 없으면 조용히 잘못 읽지 말고 멈춘다.

    부분만 마스킹된 결과를 돌려주는 것이 가장 위험하다.
    """
    result = run_cli(stdin=SAMPLE.encode("cp949"))
    assert result.returncode == 2
    assert "UTF-8" in result.stderr.decode("utf-8")
    assert not result.stdout.strip()  # 잘못 읽은 결과를 흘리지 않는다


def test_scan_reports_detections_as_utf8_json():
    result = run_cli("--scan", SAMPLE)
    assert result.returncode == 0
    payload = result.stdout.decode("utf-8")
    assert '"rrn"' in payload
    assert "800101-1234560" in payload  # --scan은 탐지 리포트라 원문을 그대로 보여준다


# --- --llm 오류 경로 (#420) ---
# 모델 응답을 가짜로 바꿔야 해서 별도 프로세스가 아니라 같은 프로세스에서 main()을 부른다.
# 위의 인코딩 회귀 테스트와 목적이 다르다. 여기서는 두 가지만 본다.
#   1) 오류가 나도 트레이스백 없이 안내 메시지와 종료 코드 1로 끝나는가
#   2) 그 메시지에 원문(모델이 뽑은 이름)이 새지 않는가


class _FakeResponse:
    """urlopen 컨텍스트 매니저 흉내 — 모델 응답 본문만 돌려준다."""

    def __init__(self, response_field: str) -> None:
        self._body = json.dumps({"response": response_field}).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _run_main_in_process(monkeypatch, capsys, *args: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["maskingtape", *args])
    code = cli.main()
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_llm_malformed_response_exits_with_message_not_traceback(monkeypatch, capsys):
    """--llm에서 모델이 names를 리스트가 아닌 값으로 주면 종료 코드 1과 안내 메시지로 끝난다.

    #416이 ruff TRY004에 맞춰 이 오류를 RuntimeError에서 TypeError로 바꿨는데, CLI는
    RuntimeError만 잡고 있어 트레이스백으로 종료했다(#420). 응답 본문에는 모델이 뽑은
    이름이 들어 있을 수 있으므로 어떤 출력에도 원문이 나오면 안 된다.
    """
    monkeypatch.setattr(
        name_llm.urllib.request, "urlopen", lambda *_a, **_kw: _FakeResponse('{"names": "김철수"}')
    )
    code, out, err = _run_main_in_process(monkeypatch, capsys, "--llm", "고객 김철수님")
    assert code == 1
    assert "이름 목록" in err
    assert "names=str" in err  # 실제 원인(names가 문자열)을 알려 준다
    assert "김철수" not in err
    assert out == ""


def test_llm_unreachable_ollama_exits_with_guidance(monkeypatch, capsys):
    """Ollama에 연결하지 못하면 무엇을 확인해야 하는지 안내하고 종료 코드 1로 끝난다."""

    def _refuse(*_a, **_kw):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(name_llm.urllib.request, "urlopen", _refuse)
    code, out, err = _run_main_in_process(monkeypatch, capsys, "--llm", "고객 김철수님")
    assert code == 1
    assert "Ollama" in err
    assert out == ""
