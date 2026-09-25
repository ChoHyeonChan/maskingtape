# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""LLM 이름 탐지기 테스트 — 합성 데이터만 사용.

CI에는 Ollama가 없으므로 가짜 client를 주입해 순수 로직(위치 변환·환각 방어)만 검증한다.
실제 모델 호출은 로컬에서 `maskingtape --llm`으로 확인한다.
"""

import http.server
import json
import threading
import urllib.request

import pytest

from maskingtape.detectors import DEFAULT_MODEL, LLMNameDetector
from maskingtape.detectors.personal import name_llm


def detector(names: list[str]) -> LLMNameDetector:
    """LLM이 names를 돌려준다고 가정한 탐지기."""
    return LLMNameDetector(client=lambda _text: names)


def test_converts_model_names_into_positions():
    text = "고객 김철수님께 연락드렸습니다."
    found = detector(["김철수"]).detect(text)
    assert len(found) == 1
    assert found[0].kind == "name"
    assert found[0].text == "김철수"
    assert text[found[0].start : found[0].end] == "김철수"
    assert found[0].confidence == 0.9


def test_detects_every_occurrence_of_the_same_name():
    text = "김영희 담당자에게 전달했고, 김영희 확인 완료."
    found = detector(["김영희"]).detect(text)
    assert len(found) == 2
    assert all(text[d.start : d.end] == "김영희" for d in found)


def test_ignores_hallucinated_names_not_present_in_text():
    # 모델이 원문에 없는 이름을 지어내도 버린다
    found = detector(["박서준"]).detect("고객 김철수님께 연락드렸습니다.")
    assert found == []


def test_strips_trailing_honorific_from_model_output():
    # LLM이 "허성님"처럼 존칭을 붙여 반환해도 스팬은 이름("허성")만 잡아 gold와 정합한다
    found = detector(["허성님"]).detect("허성님 카드번호로 결제 완료")
    assert len(found) == 1
    assert found[0].text == "허성"
    assert found[0].end - found[0].start == 2


def test_does_not_over_strip_when_result_would_be_one_char():
    # 존칭을 떼면 2글자 미만이 되는 경우는 과잉 절단이므로 원본을 유지한다
    found = detector(["김씨"]).detect("김씨 확인 바랍니다")
    assert found[0].text == "김씨"


def test_returns_nothing_when_model_finds_no_names():
    assert detector([]).detect("이용 안내: 회원 가입 후 사용하세요.") == []


def test_skips_empty_or_non_string_entries():
    found = detector(["", None, "김철수"]).detect("고객 김철수님")  # type: ignore[list-item]
    assert len(found) == 1
    assert found[0].text == "김철수"


def test_blank_text_does_not_call_the_model():
    called = False

    def client(_text: str) -> list[str]:
        nonlocal called
        called = True
        return ["김철수"]

    assert LLMNameDetector(client=client).detect("   ") == []
    assert not called


def test_connection_failure_raises_actionable_error():
    # 실제 호출 경로: 아무도 듣지 않는 포트로 보내 연결 실패를 만든다
    d = LLMNameDetector(host="http://127.0.0.1:9", timeout=1.0)
    with pytest.raises(RuntimeError, match="Ollama"):
        d.detect("고객 김철수님께 연락드렸습니다.")


class _FakeResponse:
    """HTTP 응답 컨텍스트 매니저 흉내 — 모델 응답 본문만 돌려준다."""

    def __init__(self, response_field: str) -> None:
        self._body = json.dumps({"response": response_field}).encode("utf-8")

    def read(self, _amt: int | None = None) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _detector_with_model_response(monkeypatch, response_field: str) -> LLMNameDetector:
    monkeypatch.setattr(name_llm, "_open_direct", lambda *_a, **_kw: _FakeResponse(response_field))
    return LLMNameDetector()


def test_empty_json_object_means_no_names(monkeypatch):
    # 실측: 이름이 없으면 모델이 {"names": []} 대신 {}만 주기도 한다 — 오류가 아니라 빈 결과다
    d = _detector_with_model_response(monkeypatch, "{}")
    assert d.detect("작성자 정보를 확인하세요.") == []


def test_names_key_is_used_when_present(monkeypatch):
    d = _detector_with_model_response(monkeypatch, '{"names": ["김철수"]}')
    found = d.detect("고객 김철수님")
    assert [f.text for f in found] == ["김철수"]


def test_non_list_names_raises_without_leaking_the_response(monkeypatch):
    # 응답 본문에는 추출된 이름(개인정보)이 들어있을 수 있다 — 오류 메시지에 새면 안 된다
    d = _detector_with_model_response(monkeypatch, '{"names": "김철수"}')
    with pytest.raises(TypeError, match="이름 목록") as exc_info:
        d.detect("고객 김철수님")
    assert "김철수" not in str(exc_info.value)


# --- 보안: 원문이 외부로 나가지 않도록 host를 로컬로 제한한다 ---


@pytest.mark.parametrize("host", ["http://localhost:11434", "http://127.0.0.1:11434"])
def test_allows_local_hosts(host):
    assert LLMNameDetector(host=host).host == host


@pytest.mark.parametrize(
    "host",
    ["http://evil.example.com:11434", "https://api.openai.com", "http://192.168.0.5:11434"],
)
def test_rejects_remote_hosts(host):
    # 이 탐지기는 비식별화 *전* 원문을 보내므로 원격 주소를 허용하면 개인정보가 유출된다
    with pytest.raises(ValueError, match="로컬 주소만"):
        LLMNameDetector(host=host)


def test_rejects_non_http_scheme():
    with pytest.raises(ValueError, match="http/https"):
        LLMNameDetector(host="file:///etc/passwd")


def test_malformed_names_message_reports_the_actual_type(monkeypatch):
    """names 값의 실제 타입을 알린다. 예전엔 최상위 타입(dict)만 찍어 원인이 가려졌다(#420)."""
    d = _detector_with_model_response(monkeypatch, '{"names": "김철수"}')
    with pytest.raises(TypeError, match="names=str") as exc_info:
        d.detect("고객 김철수님")
    assert "김철수" not in str(exc_info.value)

    # 최상위가 객체가 아니면 최상위 타입을 알린다
    d = _detector_with_model_response(monkeypatch, '["김철수"]')
    with pytest.raises(TypeError, match="list") as exc_info:
        d.detect("고객 김철수님")
    assert "김철수" not in str(exc_info.value)


# --- 보안: 목적지가 로컬이어도 원문이 PC 밖으로 나가는 경로를 막는다 (#468) ---


def _start_server(respond) -> tuple[http.server.HTTPServer, list[str]]:
    """127.0.0.1의 빈 포트에 POST만 받는 테스트 서버를 띄운다. 받은 요청 경로를 목록에 쌓는다.

    respond(path)는 (상태 코드, 본문, 추가 헤더)를 돌려준다. 경로마다 다른 응답을 줄 수 있다.
    """
    hits: list[str] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path)
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            status, body, extra_headers = respond(self.path)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for key, value in extra_headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        # 리다이렉트를 따라가면 urllib은 302를 GET으로 바꿔 보낸다. 방식과 상관없이 기록해야
        # "따라가지 않았다"를 제대로 확인할 수 있다.
        do_GET = do_POST

        def log_message(self, *_args):  # 테스트 출력에 요청 줄을 찍지 않는다
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, hits


def _stop(*servers: http.server.HTTPServer) -> None:
    for server in servers:
        server.shutdown()
        server.server_close()


_NAMES_REPLY = json.dumps({"response": '{"names": ["김철수"]}'}).encode("utf-8")


def _local_ollama(path: str):
    """로컬 모델인 척하는 가짜 Ollama. /api/show에는 remote_* 없는 정보를, 생성에는 이름을 준다."""
    if path == "/api/show":
        return 200, json.dumps({"details": {"family": "qwen2"}}).encode("utf-8"), {}
    return 200, _NAMES_REPLY, {}


def test_ignores_proxy_environment_variables(monkeypatch):
    """프록시 환경변수가 있어도 Ollama 요청은 프록시를 거치지 않는다.

    예전에는 urllib이 HTTP_PROXY를 따라 원문이 든 요청을 프록시로 보냈다. 목적지가 localhost라도
    회사망처럼 원격 프록시를 쓰면 원문이 PC 밖으로 나간다. 진짜 소켓으로 확인한다: 가짜 프록시와
    가짜 Ollama를 띄우고, 요청이 프록시에는 한 번도 가지 않고 Ollama에만 가는지 본다.
    """
    # urllib.request.urlopen은 처음 불릴 때 만든 opener(그때의 프록시 설정 포함)를 전역에 캐시한다.
    # 앞선 테스트가 이미 urlopen을 불렀으면 프록시 없는 opener가 남아 버그가 가려지므로, 캐시를
    # 비워 "새 프로세스에서 처음 요청하는" 실제 CLI와 같은 조건을 만든다.
    monkeypatch.setattr(urllib.request, "_opener", None)
    ollama, ollama_hits = _start_server(_local_ollama)
    proxy, proxy_hits = _start_server(lambda _path: (502, b"", {}))
    try:
        proxy_url = f"http://127.0.0.1:{proxy.server_port}"
        for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
            monkeypatch.setenv(var, proxy_url)
        for var in ("NO_PROXY", "no_proxy"):
            monkeypatch.delenv(var, raising=False)
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}", timeout=5.0)
        found = d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama, proxy)
    assert proxy_hits == []
    assert ollama_hits == ["/api/show", "/api/generate"]
    assert [x.text for x in found] == ["김철수"]


@pytest.mark.parametrize(
    "model",
    [
        "gpt-oss:120b-cloud",
        "qwen3-coder:480b-cloud",
        "glm-4.6:cloud",
        "GPT-OSS:20B-CLOUD",
        "deepseek-v3.1-cloud",
        "foo-cloud:7b",
        "localhost:5000/ns/model:tag-cloud",
        # 끝에 문장부호를 붙여 접미어 검사를 비껴가는 이름
        "gpt-oss:120b-cloud.",
        "gpt-oss:120b-cloud-",
        "gpt-oss:120b-cloud_",
        "glm-4.6:cloud.",
        "gpt-oss-cloud.:120b",
    ],
)
def test_rejects_cloud_models(model):
    """클라우드 모델은 로컬 Ollama가 요청을 ollama.com으로 넘기므로 원문을 보내기 전에 거부한다."""
    with pytest.raises(ValueError, match="클라우드 모델"):
        LLMNameDetector(model=model)


@pytest.mark.parametrize(
    "model",
    [
        DEFAULT_MODEL,
        "qwen2.5:7b-instruct-q4_K_M",
        "llama3",
        "cloudberry:7b",
        "hf.co/bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M",
        "localhost:5000/ns/qwen:7b",
    ],
)
def test_allows_local_models(model):
    # "cloud"가 이름 앞부분에만 있는 모델은 클라우드 모델이 아니다
    assert LLMNameDetector(model=model).model == model


def test_cloud_model_is_rejected_even_with_an_injected_client():
    """모델 검사는 client 주입 여부와 상관없이 한다. 설정이 잘못됐으면 호출 경로와 무관하게 막는다."""
    with pytest.raises(ValueError, match="클라우드 모델"):
        LLMNameDetector(model="gpt-oss:120b-cloud", client=lambda _text: [])


@pytest.mark.parametrize(
    "model",
    [
        "glm-4.6:cloud:",
        "gpt-oss-cloud@sha256:ab12",
        "gpt-oss:​cloud",
        "",
        " qwen2.5:7b",
        "localhost:٥٠٠٠/qwen2.5:7b",  # 아랍 숫자 포트 — ASCII 숫자만 받는다
    ],
)
def test_rejects_malformed_model_names(model):
    """끝 콜론·다이제스트·보이지 않는 문자처럼 이름 검사를 비껴갈 수 있는 형태는 형식에서 거른다."""
    with pytest.raises(ValueError, match="모델 이름 형식"):
        LLMNameDetector(model=model)


@pytest.mark.parametrize(
    "host",
    [
        "http://evil.example.com@localhost:11434",  # urlparse는 localhost로 보지만 urllib은 전체로 접속
        "http://user:pw@127.0.0.1:11434",
        "http://evil.example.com:80\\@localhost:11434",
        "http://localhost:1:2",
    ],
)
def test_rejects_hosts_whose_real_target_differs(host):
    """검사한 주소와 실제로 접속하는 주소가 달라질 수 있는 형식은 거부한다."""
    with pytest.raises(ValueError):
        LLMNameDetector(host=host)


def test_host_is_rebuilt_from_validated_parts():
    """검증한 부품으로 주소를 다시 조립해 쓴다. 대소문자·끝 슬래시는 정리되고 IPv6는 대괄호로 감싼다."""
    assert LLMNameDetector(host="http://LOCALHOST:11434/").host == "http://localhost:11434"
    assert LLMNameDetector(host="http://[::1]:11434").host == "http://[::1]:11434"


def test_refuses_a_model_that_ollama_reports_as_remote():
    """이름을 바꾼 클라우드 모델(ollama cp 별칭)도, Ollama가 원격이라고 알려 오면 보내기 전에 멈춘다."""

    def respond(path):
        if path == "/api/show":
            remote = {"remote_host": "https://ollama.com:443", "remote_model": "gpt-oss:120b"}
            return 200, json.dumps(remote).encode("utf-8"), {}
        return 200, _NAMES_REPLY, {}

    ollama, hits = _start_server(respond)
    try:
        d = LLMNameDetector(model="my-alias:latest", host=f"http://127.0.0.1:{ollama.server_port}")
        with pytest.raises(RuntimeError, match="클라우드 모델") as exc_info:
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama)
    assert hits == ["/api/show"]  # 원문이 실리는 /api/generate는 한 번도 불리지 않았다
    assert "김철수" not in str(exc_info.value)


@pytest.mark.parametrize(("body", "error"), [(b"not json", RuntimeError), (b"[]", TypeError)])
def test_unreadable_model_info_is_refused(body, error):
    """모델 정보를 확인하지 못하면(JSON이 아니거나 객체가 아닌 응답) 보내지 않는 쪽으로 멈춘다."""

    def respond(path):
        if path == "/api/show":
            return 200, body, {}
        return 200, _NAMES_REPLY, {}

    ollama, hits = _start_server(respond)
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}")
        with pytest.raises(error, match="확인하지 못해"):
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama)
    assert hits == ["/api/show"]


@pytest.mark.parametrize("redirected_path", ["/api/show", "/api/generate"])
@pytest.mark.parametrize("code", [302, 307])
def test_does_not_follow_redirects(redirected_path, code):
    """로컬 서버가 다른 주소로 리다이렉트해도 따라가지 않는다. 따라간 쪽이 받는 요청은 0이어야 한다."""
    elsewhere, elsewhere_hits = _start_server(lambda _path: (200, _NAMES_REPLY, {}))

    def respond(path):
        if path == redirected_path:
            return code, b"", {"Location": f"http://127.0.0.1:{elsewhere.server_port}{path}"}
        return _local_ollama(path)

    ollama, _hits = _start_server(respond)
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}")
        with pytest.raises(RuntimeError):
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama, elsewhere)
    assert elsewhere_hits == []


def test_checks_host_and_model_again_right_before_sending(monkeypatch):
    """객체를 만든 뒤 host·model을 바꿔도, 원문을 보내기 직전에 다시 검사해 막는다."""

    def _must_not_send(*_a, **_kw):
        raise AssertionError("검사를 통과하지 못한 설정으로 요청을 보냈다")

    monkeypatch.setattr(name_llm, "_open_direct", _must_not_send)
    d = LLMNameDetector()
    d.model = "gpt-oss:120b-cloud"
    with pytest.raises(ValueError, match="클라우드 모델"):
        d.detect("고객 김철수님께 연락드렸습니다.")
    d = LLMNameDetector()
    d.host = "http://evil.example.com:11434"
    with pytest.raises(ValueError, match="로컬 주소만"):
        d.detect("고객 김철수님께 연락드렸습니다.")


def test_model_info_is_checked_before_every_request():
    """원격 모델 확인은 원문을 보내기 직전마다 한다.

    한 번 확인하고 기억해 두면, 그사이 같은 이름이 원격 모델로 바뀌었을 때 놓친다. 두 번째 요청
    전에 Ollama가 원격이라고 답하도록 바꿔서, 두 번째 원문은 보내지 않는지 본다.
    """
    state = {"remote": False}

    def respond(path):
        if path == "/api/show":
            info = {"remote_host": "https://ollama.com:443"} if state["remote"] else {}
            return 200, json.dumps(info).encode("utf-8"), {}
        return 200, _NAMES_REPLY, {}

    ollama, hits = _start_server(respond)
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}")
        d.detect("고객 김철수님께 연락드렸습니다.")
        state["remote"] = True  # 같은 이름이 원격 모델로 바뀐 상황
        with pytest.raises(RuntimeError, match="클라우드 모델"):
            d.detect("고객 김철수님께 다시 연락드렸습니다.")
    finally:
        _stop(ollama)
    assert hits == ["/api/show", "/api/generate", "/api/show"]


def test_default_host_is_ipv4_loopback():
    """기본 주소는 127.0.0.1이다. Windows에서 localhost는 IPv6를 먼저 시도해 요청마다 약 2초를 기다린다."""
    assert LLMNameDetector().host == "http://127.0.0.1:11434"


@pytest.mark.parametrize("value", ["", None, 0, "https://ollama.com:443"])
def test_remote_key_counts_even_when_its_value_is_empty(value):
    """remote_host 키가 있기만 해도 원격으로 본다. Ollama는 로컬 모델에 이 키를 넣지 않는다."""

    def respond(path):
        if path == "/api/show":
            return 200, json.dumps({"remote_host": value}).encode("utf-8"), {}
        return 200, _NAMES_REPLY, {}

    ollama, hits = _start_server(respond)
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}")
        with pytest.raises(RuntimeError, match="클라우드 모델"):
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama)
    assert hits == ["/api/show"]


def test_ollama_error_status_is_reported_as_such():
    """Ollama가 오류로 답하면(모델 없음 404) '연결 실패'가 아니라 HTTP 오류로 알린다."""
    ollama, _hits = _start_server(lambda _path: (404, b'{"error": "model not found"}', {}))
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}")
        with pytest.raises(RuntimeError, match="HTTP 404") as exc_info:
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama)
    assert "김철수" not in str(exc_info.value)


def test_truncated_response_stops_before_sending_the_text():
    """모델 정보 응답이 중간에 끊기면 원격 여부를 확인하지 못한 것으로 보고, 원문은 보내지 않는다."""
    hits: list[str] = []

    class Truncating(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path)
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(200)
            self.send_header("Content-Length", "1000")  # 1000바이트라고 해 놓고
            self.end_headers()
            self.wfile.write(b'{"details"')  # 10바이트만 보내고 끊는다
            self.close_connection = True

        def log_message(self, *_args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Truncating)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{server.server_port}", timeout=5.0)
        with pytest.raises(RuntimeError):
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(server)
    assert hits == ["/api/show"]  # 원문이 실리는 /api/generate는 보내지 않았다


def test_connection_reset_is_reported_without_traceback(monkeypatch):
    """응답 도중 연결이 리셋돼도(ConnectionResetError) 안내가 담긴 RuntimeError로 끝난다.

    예전에는 URLError·TimeoutError만 잡아서 이 오류가 빠져나가 CLI가 트레이스백으로 끝났다.
    """

    def _reset(*_a, **_kw):
        raise ConnectionResetError("connection reset by peer")

    monkeypatch.setattr(name_llm, "_open_direct", _reset)
    with pytest.raises(RuntimeError, match="통신하지 못했습니다"):
        LLMNameDetector().detect("고객 김철수님께 연락드렸습니다.")


def test_oversized_response_is_refused(monkeypatch):
    """응답이 상한을 넘으면 읽다 말고 멈춘다. 로컬 서버가 큰 응답으로 메모리를 채우지 못하게 한다."""
    monkeypatch.setattr(name_llm, "_MAX_RESPONSE_BYTES", 100)
    ollama, hits = _start_server(lambda _path: (200, b'{"details": "' + b"x" * 500 + b'"}', {}))
    try:
        d = LLMNameDetector(host=f"http://127.0.0.1:{ollama.server_port}")
        with pytest.raises(RuntimeError, match="너무 큽니다"):
            d.detect("고객 김철수님께 연락드렸습니다.")
    finally:
        _stop(ollama)
    assert hits == ["/api/show"]  # 원문이 실리는 /api/generate까지 가지 않았다
