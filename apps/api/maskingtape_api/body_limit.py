# SPDX-License-Identifier: Apache-2.0

"""요청 바디 크기 상한 — 선언된 Content-Length가 아니라 실제로 흘러온 바이트로 막는다.

동작:
1. Content-Length가 상한을 넘으면 바디를 읽기 전에 즉시 413으로 끊는다(빠른 경로).
2. 그 헤더가 없거나(chunked 전송) 숫자가 아니어도, 바디를 흘려보내며 세다가
   상한을 넘는 순간 413으로 끊는다.

보안: 헤더만 검사하면 `Transfer-Encoding: chunked`로 보내거나 Content-Length를
생략하는 것만으로 상한을 우회할 수 있고, 그러면 ASGI 서버가 바디 전체를 메모리에
올린 뒤에야 pydantic 길이 제한에 걸린다 — 그 사이 메모리 고갈을 노릴 수 있다.
그래서 "선언값을 믿는 검사"가 아니라 "실제 바이트를 세는 검사"로 둔다.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from maskingtape_api.errors import error_response


class RequestBodyTooLarge(HTTPException):
    """바디가 상한을 넘었다.

    `HTTPException`을 상속하는 이유: 이 예외는 라우트 핸들러가 바디를 읽는 도중
    (`await request.json()`) 터지는데, FastAPI는 그 구간에서 일반 예외를 잡아
    400 "error parsing the body"로 바꿔버린다. `HTTPException`만 그대로 다시
    던져주므로(fastapi/routing.py의 `except HTTPException: raise`), 이 계열로 두어야
    413이라는 의미가 응답까지 살아서 간다.
    """

    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="request body too large",
        )
        self.max_bytes = max_bytes


async def request_body_too_large_handler(
    _request: Request,
    exc: RequestBodyTooLarge,
) -> JSONResponse:
    """413을 다른 에러들과 같은 응답 형식으로 돌려준다."""
    return _too_large_response(exc.max_bytes)


def _too_large_response(max_bytes: int) -> JSONResponse:
    return error_response(
        status.HTTP_413_CONTENT_TOO_LARGE,
        "request_body_too_large",
        f"request body must be at most {max_bytes} bytes.",
        {"max_bytes": max_bytes},
    )


class BodySizeLimitMiddleware:
    """실제 수신 바이트 수로 요청 바디 상한을 강제하는 ASGI 미들웨어.

    Starlette의 `@app.middleware("http")`(BaseHTTPMiddleware)로는 이 일을 할 수 없다 —
    거기서 `call_next`는 넘겨준 Request의 receive가 아니라 원본 receive를 그대로 쓰기
    때문에, 바디 스트림을 감싸도 실제 읽기 경로에 끼어들지 못한다. 그래서 순수 ASGI로 둔다.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _declared_content_length(scope)
        if declared is not None and declared > self.max_bytes:
            await self._send_too_large(scope, receive, send)
            return

        received = 0
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge(self.max_bytes)
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, send_wrapper)
        except RequestBodyTooLarge:
            # 이미 응답 헤더가 나갔으면 덧붙일 수 없다 — 그땐 조용히 끝낸다.
            if not response_started:
                await self._send_too_large(scope, receive, send)

    async def _send_too_large(self, scope: Scope, receive: Receive, send: Send) -> None:
        await _too_large_response(self.max_bytes)(scope, receive, send)


def _declared_content_length(scope: Scope) -> int | None:
    """Content-Length 헤더를 정수로 읽는다 — 없거나 이상하면 None(=흘려보내며 센다)."""
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            try:
                parsed = int(value)
            except ValueError:
                return None
            return parsed if parsed >= 0 else None
    return None
