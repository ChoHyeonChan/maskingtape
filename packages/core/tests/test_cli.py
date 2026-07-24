"""CLI 통합 테스트 — 표준입출력 인코딩까지 검증하므로 실제 프로세스를 띄운다.

여기 쓰는 개인정보는 전부 합성(가짜)이다. 주민등록번호는 체크섬만 맞춘 값이다.
"""

from __future__ import annotations

import os
import subprocess
import sys

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
