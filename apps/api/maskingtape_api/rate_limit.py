# SPDX-FileCopyrightText: 2026 The maskingtape Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import Request, status
from fastapi.responses import JSONResponse

from maskingtape_api.errors import error_response


@dataclass(frozen=True)
class RateLimitResult:
    """요청 처리 여부와 재시도 힌트를 분리해 핸들러가 HTTP 표현만 맡게 한다."""

    allowed: bool
    retry_after_seconds: int | None = None


class RateLimitExceeded(RuntimeError):
    """Raised when a client exceeds the configured request window."""

    def __init__(
        self,
        retry_after_seconds: int,
        limit: int,
        window_seconds: int,
    ) -> None:
        """429 응답에 필요한 수치만 보존하고 요청 내용은 담지 않는다."""
        super().__init__("rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds
        self.limit = limit
        self.window_seconds = window_seconds


class InMemoryRateLimiter:
    """Small rolling-window rate limiter keyed by client identifier."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        max_buckets: int = 10_000,
        now: Callable[[], float] = monotonic,
    ) -> None:
        """메모리 기반 제한기라 입력값을 작게 검증해 잘못된 설정을 빨리 드러낸다.

        이 카운터는 프로세스 안에서만 공유된다. Vercel serverless처럼 인스턴스가 여럿
        생기는 배포에서는 전역 제한이 아니라 best-effort 보호이며, 강한 제한이 필요하면
        플랫폼 보호나 외부 공유 저장소가 필요하다.
        """
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")
        if max_buckets < 1:
            raise ValueError("max_buckets must be at least 1")

        self.limit = limit
        self.window_seconds = window_seconds
        self.max_buckets = max_buckets
        self._now = now
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()
        self._next_prune_at = 0.0

    def check(self, key: str) -> RateLimitResult:
        """한 키의 현재 창 안 요청 수를 갱신하고 허용 여부를 돌려준다.

        요청이 들어올 때마다 만료된 타임스탬프를 지워 rolling window를 유지한다. 새 키는
        LRU 상한을 먼저 확인해, 공격자가 임의 키를 계속 만들어도 dict가 끝없이 자라지 않게
        한다.
        """
        now = self._now()
        with self._lock:
            self._prune_expired_buckets(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                self._evict_lru_bucket_if_needed()
                bucket = deque()
                self._buckets[key] = bucket
            else:
                self._buckets.move_to_end(key)

            self._drop_expired(bucket, now)
            if len(bucket) >= self.limit:
                retry_after = max(1, ceil(bucket[0] + self.window_seconds - now))
                return RateLimitResult(
                    allowed=False,
                    retry_after_seconds=retry_after,
                )

            bucket.append(now)
            return RateLimitResult(allowed=True)

    @property
    def bucket_count(self) -> int:
        """테스트와 운영 점검에서 버킷 증가가 통제되는지 볼 수 있게 노출한다."""
        return len(self._buckets)

    def _drop_expired(self, bucket: deque[float], now: float) -> None:
        """창 밖의 요청 기록을 즉시 버려 다음 판단이 오래된 요청에 끌리지 않게 한다."""
        window_start = now - self.window_seconds
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

    def _prune_expired_buckets(self, now: float) -> None:
        """빈 버킷을 주기적으로 제거해 장시간 실행 서버의 메모리 누수를 막는다."""
        if now < self._next_prune_at:
            return

        for key in list(self._buckets):
            bucket = self._buckets[key]
            self._drop_expired(bucket, now)
            if not bucket:
                del self._buckets[key]
        self._next_prune_at = now + min(60, self.window_seconds)

    def _evict_lru_bucket_if_needed(self) -> None:
        """서로 다른 키를 무한히 주입하는 DoS를 막기 위해 가장 오래 안 쓴 버킷을 버린다."""
        while len(self._buckets) >= self.max_buckets:
            self._buckets.popitem(last=False)


def enforce_rate_limit(request: Request) -> None:
    """라우터 의존성에서 공통 rate limit 정책을 적용한다.

    라우터마다 같은 코드를 두면 `/scan`과 `/anonymize`의 보안 정책이 어긋나기 쉬워,
    앱 상태의 limiter와 신뢰 헤더 설정을 한 곳에서 읽는다.
    """
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    trusted_headers: tuple[str, ...] = getattr(
        request.app.state, "trusted_client_ip_headers", ()
    )
    result = limiter.check(_client_key(request, trusted_headers))
    if result.allowed:
        return

    raise RateLimitExceeded(
        retry_after_seconds=result.retry_after_seconds or limiter.window_seconds,
        limit=limiter.limit,
        window_seconds=limiter.window_seconds,
    )


async def rate_limit_exception_handler(
    _request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """429 응답에 Retry-After를 붙여 정상 클라이언트가 기다릴 시간을 알게 한다."""
    return error_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limit_exceeded",
        "too many requests.",
        {"limit": exc.limit, "window_seconds": exc.window_seconds},
        {"Retry-After": str(exc.retry_after_seconds)},
    )


def _client_key(request: Request, trusted_headers: tuple[str, ...] = ()) -> str:
    """rate limit 버킷 키를 고른다 — 신뢰할 수 있다고 설정된 헤더만 본다.

    보안: 클라이언트가 값을 바꿀 수 있는 헤더를 무조건 신뢰하면, 매 요청 헤더만 바꿔
    새 버킷을 만들어 제한을 통째로 우회할 수 있다. 그래서 목록은 설정에서 받고
    (기본은 비어 있음), 비어 있으면 위조할 수 없는 TCP 소켓 주소만 쓴다.
    어떤 헤더를 신뢰할지는 settings._default_trusted_client_ip_headers 참고.
    """
    for header in trusted_headers:
        client_ip = _first_header_value(request.headers.get(header))
        if client_ip:
            return _client_ip_bucket_key(client_ip)

    if request.client:
        return _client_ip_bucket_key(request.client.host)
    return "unknown"


def _client_ip_bucket_key(value: str) -> str:
    try:
        address = ip_address(value)
    except ValueError:
        return value

    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped

    if address.version == 6:
        return str(ip_network(f"{address}/64", strict=False))
    return str(address)


def _first_header_value(value: str | None) -> str | None:
    """프록시 체인 헤더에서 앱이 신뢰하기로 한 첫 값을 버킷 키로 쓴다.

    헤더 사용 여부는 `_client_key`가 이미 제한하므로, 여기서는 공백과 빈 값만 정리해
    같은 클라이언트가 불필요하게 다른 키로 갈라지지 않게 한다.
    """
    if value is None:
        return None
    first_value = value.split(",", maxsplit=1)[0].strip()
    return first_value or None
