"""이름 탐지기 — 로컬 LLM(Ollama) 문맥 판단판.

규칙판(name.py)은 성씨 사전 + 앞뒤 문맥 단서에 의존해서, 단서 단어가 성씨와 무관하게
등장하면 오탐한다("이용 안내"의 '이용'을 이+용으로 봄). 이 탐지기는 문장 전체를 로컬
LLM에 보내 "사람 이름만" 뽑게 해 그 한계를 넘는다.

동작 원리:
1. 로컬 Ollama(기본 http://localhost:11434)에 문장을 보내 이름만 JSON으로 받는다.
   **외부 상용 API는 절대 호출하지 않는다** — 로컬 오픈웨이트 모델만 쓴다.
2. 받은 이름 문자열을 원문에서 찾아 위치(start/end)를 만든다. 원문에 없는 문자열은
   모델의 환각이므로 버린다(같은 이름이 여러 번 나오면 전부 탐지한다).
3. 문맥 판단이라 확신도는 규칙판(0.5~0.75)보다 높은 0.9로 준다 — 다만 모델 출력이므로
   1.0(정규식+체크섬으로 확정되는 주민번호 등)과는 구분한다.

**Ollama가 설치·실행돼 있어야 동작한다.** 그래서 default_detectors()에는 넣지 않는다 —
CLI `--llm`이나 llm_detectors()로 명시적으로 선택할 때만 쓴다(없는 환경에서 조용히
망가지지 않도록, 연결 실패 시 무엇을 확인해야 하는지 알려주는 오류를 낸다).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from maskingtape.detectors.base import Detector
from maskingtape.detectors.name import has_name_candidate
from maskingtape.types import Detection

DEFAULT_MODEL = "qwen2.5:7b"  # Apache-2.0 (Qwen2.5의 3B·72B만 비상업 제한이라 7B를 쓴다)
DEFAULT_HOST = "http://localhost:11434"

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
    if parsed.hostname not in _LOCAL_HOSTNAMES:
        raise ValueError(
            f"로컬 주소만 허용합니다 (받은 host: {parsed.hostname!r}). "
            "비식별화 전 원문이 외부로 전송되는 것을 막기 위한 제한입니다 — "
            f"허용: {', '.join(sorted(_LOCAL_HOSTNAMES))}"
        )
    return host.rstrip("/")


class LLMNameDetector(Detector):
    """로컬 Ollama로 문맥을 읽어 사람 이름을 찾는 탐지기 (Ollama 필요).

    보안: host는 **로컬 주소만** 허용한다. 이 탐지기는 비식별화 *전* 원문을 그대로
    모델에 보내므로, 원격 주소를 허용하면 개인정보가 외부로 나간다.
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
        self.model = model
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
        body = json.dumps(
            {
                "model": self.model,
                "system": _SYSTEM_PROMPT,
                "prompt": text,
                "stream": False,
                "format": "json",  # 유효한 JSON 응답을 강제한다
                "options": {"temperature": 0},  # 같은 입력에 같은 결과 (재현성)
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"로컬 Ollama에 연결하지 못했습니다({self.host}). "
                f"Ollama가 실행 중인지, `ollama pull {self.model}`로 모델을 받았는지 확인하세요."
            ) from exc

        try:
            parsed = json.loads(payload["response"])
        except (KeyError, ValueError) as exc:
            raise RuntimeError(
                f"모델 {self.model}의 응답을 JSON으로 읽지 못했습니다 (format=json 지원 모델인지 확인)."
            ) from exc

        # 이름이 하나도 없으면 모델이 {"names": []} 대신 {}만 주기도 한다(실측) — 빈 목록으로 본다
        names = parsed.get("names", []) if isinstance(parsed, dict) else None
        if not isinstance(names, list):
            # 응답 본문에는 추출된 이름(개인정보)이 들어있을 수 있으므로 타입만 알린다.
            raise RuntimeError(
                f"모델 {self.model}의 응답에 이름 목록(names)이 없습니다 "
                f"(받은 형태: {type(parsed).__name__}). 응답 본문은 개인정보가 섞일 수 있어 표시하지 않습니다."
            )
        return names

    def _to_detections(self, text: str, names: list[str]) -> list[Detection]:
        """이름 문자열을 원문 위치로 바꾼다. 원문에 없으면(환각) 버린다."""
        found: list[Detection] = []
        for name in names:
            if not isinstance(name, str) or not name:
                continue
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
