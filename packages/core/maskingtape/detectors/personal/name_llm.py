# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

"""이름 탐지기 — 로컬 LLM(Ollama) 문맥 판단판.

규칙판(name.py)은 성씨 사전 + 앞뒤 문맥 단서에 의존해서, 단서 단어가 성씨와 무관하게
등장하면 오탐한다("이용 안내"의 '이용'을 이+용으로 봄). 이 탐지기는 문장 전체를 로컬
LLM에 보내 "사람 이름만" 뽑게 해 그 한계를 넘는다.

동작 원리:
1. 로컬 Ollama(기본 http://127.0.0.1:11434)에 문장을 보내 이름만 JSON으로 받는다.
   **외부 상용 API는 절대 호출하지 않는다** — 로컬 오픈웨이트 모델만 쓴다.
   원문이 PC 밖으로 나가는 알려진 길을 실행되는 검사로 막는다.
   - 목적지가 원격 주소, 또는 검사와 실제 접속이 달라지는 주소("evil@localhost")
     → _require_local_host가 거부하고, 검증한 부품으로 주소를 다시 조립해 쓴다(#468)
   - 목적지는 로컬인데 프록시를 거치거나 리다이렉트로 다른 곳에 감
     → _open_direct가 프록시 없이 직접 연결하고 리다이렉트는 따라가지 않는다(#468)
   - 목적지는 로컬인데 Ollama가 클라우드로 넘김 → 이름으로 한 번(_require_local_model),
     원문을 보내기 직전마다 Ollama가 알려 주는 모델 정보로 한 번(_require_not_remote) 거부한다(#468)
2. 받은 이름 문자열을 원문에서 찾아 위치(start/end)를 만든다. 원문에 없는 문자열은
   모델의 환각이므로 버린다(같은 이름이 여러 번 나오면 전부 탐지한다).
3. 문맥 판단이라 확신도는 규칙판(0.5~0.75)보다 높은 0.9로 준다 — 다만 모델 출력이므로
   1.0(정규식+체크섬으로 확정되는 주민번호 등)과는 구분한다.

**Ollama가 설치·실행돼 있어야 동작한다.** 그래서 default_detectors()에는 넣지 않는다 —
CLI `--llm`이나 llm_detectors()로 명시적으로 선택할 때만 쓴다(없는 환경에서 조용히
망가지지 않도록, 연결 실패 시 무엇을 확인해야 하는지 알려주는 오류를 낸다).
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from maskingtape.detectors.base import Detector
from maskingtape.detectors.personal.name import has_name_candidate
from maskingtape.types import Detection

DEFAULT_MODEL = "qwen2.5:7b"  # Apache-2.0 (Qwen2.5의 3B·72B만 비상업 제한이라 7B를 쓴다)
# 기본 주소는 localhost가 아니라 127.0.0.1이다. Ollama는 기본으로 127.0.0.1에서만 기다리는데,
# Windows는 localhost를 IPv6(::1)로 먼저 시도해 요청마다 약 2초를 기다린 뒤에야 붙는다
# (실측: localhost 2.05초, 127.0.0.1 0.01~0.03초). 요청마다 모델 정보를 확인하므로 이 대기가
# 두 배가 되지 않게 한다(#468). 데스크톱 앱의 Ollama 상태 확인도 같은 주소를 쓴다.
DEFAULT_HOST = "http://127.0.0.1:11434"

# 원문(개인정보)을 그대로 실어 보내는 요청이라 **로컬 주소만 허용한다**.
# 원격 host를 허용하면 비식별화 전 텍스트가 외부로 나가고, 대회 규정(외부 AI API 호출 금지)도 어긋난다.
_LOCAL_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1"})

# 지명·기관명·일반명사를 이름으로 뱉지 않도록 역할을 좁혀 지시한다.
_SYSTEM_PROMPT = (
    "너는 한국어 텍스트에서 실제 '사람 이름(인명)'만 추출하는 도구다. "
    "지명·기관명·일반명사·제품명은 절대 포함하지 마라. "
    'JSON만 출력한다: {"names": ["이름1", ...]}. 이름이 없으면 {"names": []}.'
)


def _require_local_host(host: str) -> str:
    """로컬 주소가 아니면 거부한다 — 개인정보 원문이 외부로 나가는 걸 코드로 막는다.

    docstring의 "외부 API를 부르지 않는다"는 약속을 주석이 아니라 실행되는 검사로 강제한다.
    """
    parsed = urllib.parse.urlparse(host)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"host는 http/https URL이어야 합니다 (받은 값: {host!r})")
    # urlparse는 "@" 뒤만 hostname으로 보지만, urllib은 "evil.com@localhost" 같은 netloc 전체를
    # 접속 대상으로 쓴다. 검사한 주소와 실제로 접속하는 주소가 달라지는 형식은 통째로 거부한다(#468).
    # 사용자 정보(user@)·역슬래시는 Ollama 주소에 쓸 일이 없다.
    has_userinfo = parsed.username is not None or parsed.password is not None
    if has_userinfo or "@" in parsed.netloc or "\\" in host:
        raise ValueError(f"host에 사용자 정보(@)나 역슬래시를 넣을 수 없습니다. 예: {DEFAULT_HOST}")
    if parsed.hostname not in _LOCAL_HOSTNAMES:
        raise ValueError(
            f"로컬 주소만 허용합니다 (받은 host: {parsed.hostname!r}). "
            "비식별화 전 원문이 외부로 전송되는 것을 막기 위한 제한입니다 — "
            f"허용: {', '.join(sorted(_LOCAL_HOSTNAMES))}"
        )
    try:
        port = parsed.port  # "localhost:1:2"처럼 포트가 숫자가 아니면 여기서 ValueError가 난다
    except ValueError:
        raise ValueError(f"host의 포트가 올바르지 않습니다 (받은 값: {host!r})") from None
    # 검증한 부품(scheme·hostname·port)만으로 주소를 다시 만든다. 원래 문자열을 그대로 쓰면
    # 검사에 안 걸린 부분이 실제 요청에 섞일 수 있다. IPv6 주소는 대괄호로 감싼다.
    netloc = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    if port is not None:
        netloc += f":{port}"
    return f"{parsed.scheme}://{netloc}"


# Ollama 모델 이름으로 쓸 수 있는 형태만 받는다: [레지스트리[:포트]/][네임스페이스/]이름[:태그].
# ASCII 영문·숫자와 . _ - / : 만 허용한다(re.ASCII라 \d도 0~9만 받는다). 끝에 붙은 콜론,
# "@다이제스트", 보이지 않는 문자, 비슷하게 생긴 다른 글자로 아래 클라우드 검사를 비껴가는 이름을
# 미리 걸러 낸다(#468).
_MODEL_NAME_RE = re.compile(
    r"(?:[A-Za-z0-9.\-]+(?::\d{1,5})?/)?[A-Za-z0-9][A-Za-z0-9._\-/]*(?::[A-Za-z0-9._\-]+)?",
    re.ASCII,
)


def _require_local_model(model: str) -> str:
    """클라우드 모델이면 거부한다. 목적지가 localhost여도 원문이 ollama.com으로 나가기 때문이다(#468).

    Ollama의 클라우드 모델은 이름이 "cloud"로 끝난다(예: gpt-oss:120b-cloud, glm-4.6:cloud. Ollama
    앱도 이 접미어로 클라우드 모델을 가린다). 이런 모델을 받으면 Ollama는 ollama.com에 로그인된
    상태에서 요청을 그대로 클라우드로 넘긴다. 대회 규정도 외부 API로만 도는 모델을 금지한다
    (제9조 ①항, 별표 2).
    애매하면 거부하는 쪽이 안전하므로 넓게 막는다.
    - 끝의 . _ - 를 뗀 이름이 "cloud"로 끝나면 거부("…-cloud.", "…-cloud-"로 비껴가지 못하게)
    - : / . _ - 로 나눈 조각 중 하나라도 "cloud"이면 거부("gpt-oss-cloud.:120b" 등)
    그래서 "cloud"라는 조각이 든 로컬 모델 이름도 거부된다. "cloudberry"처럼 낱말 일부면 괜찮다.

    이름으로는 `ollama cp`로 붙인 별칭을 알 수 없다. 그건 원문을 보내기 직전마다 Ollama가 알려
    주는 모델 정보로 다시 확인한다(LLMNameDetector._require_not_remote).
    """
    if not _MODEL_NAME_RE.fullmatch(model):
        raise ValueError(
            f"모델 이름 형식이 올바르지 않습니다 (받은 모델: {model!r}). "
            f"영문·숫자와 . _ - / : 만 쓸 수 있습니다. 예: {DEFAULT_MODEL}"
        )
    lowered = model.lower()
    pieces = re.split(r"[:/._\-]", lowered)
    if lowered.rstrip("._-").endswith("cloud") or "cloud" in pieces:
        # 모델 이름은 사용자가 준 설정값이라 메시지에 넣어도 된다. 원문은 절대 넣지 않는다.
        raise ValueError(
            f"클라우드 모델은 쓸 수 없습니다 (받은 모델: {model!r}). "
            "Ollama가 요청을 ollama.com으로 넘겨 비식별화 전 원문이 외부로 나갑니다. "
            f"로컬 모델(예: {DEFAULT_MODEL})을 쓰세요."
        )
    return model


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """리다이렉트를 따라가지 않는다(#468).

    Ollama API는 리다이렉트를 쓰지 않는다. 따라가면 host 검사를 거친 적 없는 주소로 요청이 간다.
    None을 돌려주면 urllib이 따라가지 않고 HTTPError를 낸다.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# 원문을 싣는 요청이라 프록시를 쓰지 않는다(#468).
# urllib.request.urlopen은 HTTP_PROXY 같은 환경변수(Windows에서는 시스템 프록시 설정까지)를
# 그대로 따라가서, 목적지가 localhost여도 요청 전체가 프록시를 거친다. 회사망처럼 원격 프록시를
# 쓰는 환경이면 원문이 PC 밖으로 나간다. ProxyHandler({})로 프록시 목록을 비운 opener를 따로
# 만들어, 이 모듈의 요청은 환경과 상관없이 항상 직접 연결로만 보낸다. 리다이렉트도 따라가지 않는다.
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirects)

# Ollama 응답을 읽는 상한. 모델 정보(/api/show)가 약 30KB, 이름 목록 응답은 그보다 훨씬 작다.
# 로컬 서버가 비정상적으로 큰 응답을 줘도 메모리를 다 쓰지 않게 여기서 끊는다(#468).
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _open_direct(request: urllib.request.Request, timeout: float):
    """프록시를 거치지 않고 요청을 보낸다. 로컬 Ollama 호출은 전부 이 함수 하나로만 나간다.

    한 곳으로 모아 두면 "원문이 나가는 네트워크 경로"가 이 함수뿐이라는 게 코드에서 보이고,
    테스트도 이 함수만 바꿔 끼우면 된다.
    """
    return _DIRECT_OPENER.open(request, timeout=timeout)


# LLM이 이름 뒤에 존칭을 붙여 반환하기도 한다("허성님") — 떼어 gold 스팬과 맞춘다.
# 사람 이름은 님/씨로 끝나지 않으므로 안전하다.
_HONORIFICS = ("님", "씨")


def _strip_honorific(name: str) -> str:
    """LLM 반환 이름 뒤의 존칭(님/씨)을 뗀다. 떼면 2글자 미만이 되는 경우는 과잉 절단으로
    오탐을 낼 수 있어 원본을 그대로 둔다(사람 이름은 최소 2글자)."""
    for suffix in _HONORIFICS:
        if name.endswith(suffix):
            stripped = name[: -len(suffix)]
            if len(stripped) >= 2:
                return stripped
    return name


class LLMNameDetector(Detector):
    """로컬 Ollama로 문맥을 읽어 사람 이름을 찾는 탐지기 (Ollama 필요).

    보안: host는 **로컬 주소만** 허용한다. 이 탐지기는 비식별화 *전* 원문을 그대로
    모델에 보내므로, 원격 주소를 허용하면 개인정보가 외부로 나간다. 요청은 프록시·리다이렉트를
    거치지 않고, 클라우드 모델은 이름과 (요청 직전마다) Ollama 모델 정보로 두 번 거부한다(#468).
    """

    kind = "name"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        timeout: float = 120.0,
        client: Callable[[str], list[str]] | None = None,
    ) -> None:
        """client를 주입하면 Ollama 없이도 동작한다 (테스트용 — 기본은 실제 호출)."""
        self.calls = 0  # 실제로 LLM을 부른 횟수 (하이브리드 필터 효과 측정용)
        # 모델 검사는 client 주입 여부와 상관없이 한다. 설정이 잘못됐으면 어느 경로로 부르든
        # 원문을 보내기 전에, 객체를 만드는 시점에 멈춘다(#468).
        self.model = _require_local_model(model)
        # 실제 호출을 하는 경우에만 host를 검증한다 (client 주입 시엔 네트워크를 쓰지 않음)
        self.host = host.rstrip("/") if client is not None else _require_local_host(host)
        self.timeout = timeout
        self._client = client if client is not None else self._ask_ollama

    def detect(self, text: str) -> list[Detection]:
        if not text.strip():
            return []
        # 하이브리드: 규칙으로 이름 후보를 먼저 훑어, 후보가 없는 텍스트는 LLM을 건너뛴다.
        # 순수 숫자·코드처럼 이름이 있을 수 없는 입력에서 느린 LLM 호출을 아낀다.
        if not has_name_candidate(text):
            return []
        self.calls += 1
        return self._to_detections(text, self._client(text))

    def _ask_ollama(self, text: str) -> list[str]:
        """로컬 Ollama에 물어 이름 목록을 받는다. 연결·응답 문제는 안내와 함께 올린다."""
        # 원문을 보내기 직전에 host와 모델을 다시 검사한다. 객체를 만든 뒤 d.host·d.model을
        # 바꿔 생성자 검사를 비껴가는 경우까지 막는다(#468). 검증해 다시 조립한 값만 쓴다.
        host = _require_local_host(self.host)
        model = _require_local_model(self.model)
        self._require_not_remote(host, model)
        body = self._post(
            host,
            model,
            "/api/generate",
            {
                "model": model,
                "system": _SYSTEM_PROMPT,
                "prompt": text,
                "stream": False,
                "format": "json",  # 유효한 JSON 응답을 강제한다
                "options": {"temperature": 0},  # 같은 입력에 같은 결과 (재현성)
                # 모델을 메모리에 30분 상주시켜 다음 호출의 콜드스타트(재로딩) 지연을 없앤다.
                # 정확도·출력에는 영향이 없고, 유휴 시 자동으로 내려간다.
                "keep_alive": "30m",
            },
        )

        try:
            parsed = json.loads(json.loads(body)["response"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f"모델 {model}의 응답을 JSON으로 읽지 못했습니다 (format=json 지원 모델인지 확인)."
            ) from exc

        # 이름이 하나도 없으면 모델이 {"names": []} 대신 {}만 주기도 한다(실측) — 빈 목록으로 본다
        names = parsed.get("names", []) if isinstance(parsed, dict) else None
        if not isinstance(names, list):
            # 응답 본문에는 추출된 이름(개인정보)이 들어있을 수 있으므로 타입만 알린다.
            # 최상위가 객체면 names 값의 타입을, 아니면 최상위 타입을 알린다. 예전엔 항상
            # 최상위 타입(dict)만 찍어 {"names": "김철수"}처럼 names가 문자열인 경우를 가렸다(#420).
            if isinstance(parsed, dict):
                received = f"names={type(names).__name__}"
            else:
                received = type(parsed).__name__
            raise TypeError(
                f"모델 {model}의 응답에 이름 목록(names)이 없습니다 "
                f"(받은 형태: {received}). 응답 본문은 개인정보가 섞일 수 있어 표시하지 않습니다."
            )
        return names

    def _require_not_remote(self, host: str, model: str) -> None:
        """Ollama에 모델 정보를 물어, 원격(클라우드) 모델이면 원문을 보내기 전에 멈춘다(#468).

        이름 검사는 `ollama cp`로 붙인 별칭을 못 잡는다. Ollama는 원격 모델의 정보(/api/show)에
        remote_host·remote_model을 넣어 주고, 이 값은 모델 설정에 저장돼 별칭에도 따라간다(Ollama
        소스 api/types.go의 ShowResponse). 그래서 원문을 보내기 직전마다 확인한다. 한 번 확인하고
        기억해 두면, 그사이 같은 이름이 원격 모델로 바뀌었을 때 놓친다. 이 요청에는 모델 이름만
        실리고 원문은 없으며, 127.0.0.1에서는 수십 ms로 끝난다.

        키가 있기만 해도(값이 비어 있어도) 원격으로 본다. Ollama는 로컬 모델에 이 키를 아예 넣지
        않는다. 확인하지 못하면(연결 실패·이상한 응답) 보내지 않고 멈춘다.
        """
        body = self._post(host, model, "/api/show", {"model": model})
        unreadable = (
            f"Ollama가 모델 {model}의 정보를 알아볼 수 없는 형태로 돌려줬습니다. "
            "원격 모델인지 확인하지 못해 보내지 않습니다."
        )
        try:
            info = json.loads(body)
        except ValueError as exc:  # JSON이 아닌 응답
            raise RuntimeError(unreadable) from exc
        # JSON이지만 객체가 아닌 응답은 형태 오류라 TypeError로 알린다(#420과 같은 규칙).
        if not isinstance(info, dict):
            raise TypeError(unreadable)
        if "remote_host" in info or "remote_model" in info:
            raise RuntimeError(
                f"클라우드 모델은 쓸 수 없습니다 (모델: {model!r}). Ollama가 이 모델을 원격 모델로 "
                "알려 왔습니다. 요청하면 비식별화 전 원문이 외부로 나갑니다. "
                f"로컬 모델(예: {DEFAULT_MODEL})을 쓰세요."
            )

    def _post(self, host: str, model: str, path: str, payload: dict) -> bytes:
        """Ollama에 JSON을 POST하고 응답 본문을 돌려준다. 통신 문제는 안내가 담긴 RuntimeError로 바꾼다.

        요청은 _open_direct(프록시·리다이렉트 없음)로만 나간다. 오류 메시지에는 주소·모델 이름만
        넣고, 요청 본문(원문)과 응답 본문(추출된 이름)은 넣지 않는다.
        """
        request = urllib.request.Request(
            f"{host}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            # urlopen을 쓰지 않는다. 프록시 환경변수를 따라가 원문이 새기 때문이다(#468).
            with _open_direct(request, timeout=self.timeout) as response:
                body = response.read(_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # 연결은 됐지만 Ollama가 오류로 답했다(모델이 없으면 404). 리다이렉트도 따라가지 않아
            # 여기로 온다. HTTPError는 URLError의 하위 클래스라 먼저 잡아야 한다.
            raise RuntimeError(
                f"로컬 Ollama가 오류로 응답했습니다(HTTP {exc.code}, {host}{path}). "
                f"`ollama pull {model}`로 모델을 받았는지 확인하세요."
            ) from exc
        except (OSError, http.client.HTTPException) as exc:
            # 연결 실패(URLError)·타임아웃·연결 리셋(ConnectionResetError)·HTTP 규약 오류를 모두
            # 여기서 받는다. 예전에는 리셋이 빠져나가 CLI가 트레이스백으로 끝났다. 크기를 정해 읽으면
            # 중간에 끊긴 응답은 예외 없이 짧게 오는데, 그런 본문은 호출한 쪽의 JSON 해석에서 멈춘다.
            raise RuntimeError(
                f"로컬 Ollama와 통신하지 못했습니다({host}). "
                f"Ollama가 실행 중인지, `ollama pull {model}`로 모델을 받았는지 확인하세요."
            ) from exc
        if len(body) > _MAX_RESPONSE_BYTES:
            raise RuntimeError(
                f"로컬 Ollama의 응답이 너무 큽니다({_MAX_RESPONSE_BYTES // (1024 * 1024)}MB 초과, "
                f"{host}{path}). 응답을 쓰지 않고 멈춥니다."
            )
        return body

    def _to_detections(self, text: str, names: list[str]) -> list[Detection]:
        """이름 문자열을 원문 위치로 바꾼다. 원문에 없으면(환각) 버린다."""
        found: list[Detection] = []
        for name in names:
            if not isinstance(name, str) or not name:
                continue
            name = _strip_honorific(name)
            start = text.find(name)
            while start != -1:
                found.append(
                    Detection(
                        kind=self.kind,
                        start=start,
                        end=start + len(name),
                        text=name,
                        confidence=0.9,
                        detector=self.__class__.__name__,
                    )
                )
                start = text.find(name, start + len(name))
        return found
