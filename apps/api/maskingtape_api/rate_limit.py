# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import Request, status
from fastapi.responses import JSONResponse

from maskingtape_api.errors import error_response


@dataclass(frozen=True)
class RateLimitResult:
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
        return len(self._buckets)

    def _drop_expired(self, bucket: deque[float], now: float) -> None:
        window_start = now - self.window_seconds
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

    def _prune_expired_buckets(self, now: float) -> None:
        if now < self._next_prune_at:
            return

        for key in list(self._buckets):
            bucket = self._buckets[key]
            self._drop_expired(bucket, now)
            if not bucket:
                del self._buckets[key]
        self._next_prune_at = now + min(60, self.window_seconds)

    def _evict_lru_bucket_if_needed(self) -> None:
        while len(self._buckets) >= self.max_buckets:
            self._buckets.popitem(last=False)


def enforce_rate_limit(request: Request) -> None:
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    result = limiter.check(_client_key(request))
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
    return error_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limit_exceeded",
        "too many requests.",
        {"limit": exc.limit, "window_seconds": exc.window_seconds},
        {"Retry-After": str(exc.retry_after_seconds)},
    )


def _client_key(request: Request) -> str:
    for header in ("x-vercel-forwarded-for", "x-real-ip"):
        client_ip = _first_header_value(request.headers.get(header))
        if client_ip:
            return client_ip

    if request.client:
        return request.client.host
    return "unknown"


def _first_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    first_value = value.split(",", maxsplit=1)[0].strip()
    return first_value or None
