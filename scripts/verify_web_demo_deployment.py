# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


SAMPLE_TEXT = "passport M12345678 check"
SAMPLE_PII = "M12345678"


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: str

    def json(self) -> Any:
        return json.loads(self.body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the deployed maskingtape web demo.")
    parser.add_argument("base_url", help="Deployment base URL, for example https://example.vercel.app")
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help="Allow http:// URLs for local smoke tests only.",
    )
    parser.add_argument(
        "--check-rate-limit",
        action="store_true",
        help=(
            "Probe the process-local app limiter until a 429 is observed. "
            "This is not a global serverless rate-limit guarantee."
        ),
    )
    parser.add_argument(
        "--rate-limit-attempts",
        type=int,
        default=65,
        help="Maximum requests for --check-rate-limit.",
    )
    args = parser.parse_args()

    base_url = _normalized_base_url(args.base_url, allow_http=args.allow_http)

    _assert_web_root(base_url)
    _assert_health(base_url)
    _assert_scan(base_url)
    _assert_anonymize(base_url)
    _assert_cors_rejects_untrusted_origin(base_url)
    if args.check_rate_limit:
        _assert_rate_limit(base_url, args.rate_limit_attempts)

    print("deployment verification passed")
    return 0


def _normalized_base_url(value: str, allow_http: bool) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" and not (allow_http and parsed.scheme == "http"):
        raise AssertionError("deployment URL must use https")
    if not parsed.netloc:
        raise AssertionError("deployment URL must include a host")
    return value.rstrip("/") + "/"


def _assert_web_root(base_url: str) -> None:
    response = _request("GET", base_url)
    if response.status != 200:
        raise AssertionError(f"web root returned {response.status}")
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise AssertionError(f"web root did not return HTML: {content_type}")


def _assert_health(base_url: str) -> None:
    response = _request("GET", urljoin(base_url, "api/health"))
    if response.status != 200:
        raise AssertionError(f"/api/health returned {response.status}")
    if response.json() != {"status": "ok"}:
        raise AssertionError(f"/api/health returned unexpected body: {response.body}")


def _assert_scan(base_url: str) -> None:
    response = _post_json(urljoin(base_url, "api/scan"), {"text": SAMPLE_TEXT})
    if response.status != 200:
        raise AssertionError(f"/api/scan returned {response.status}: {response.body}")
    if SAMPLE_PII in response.body:
        raise AssertionError("/api/scan echoed raw PII in the response body")

    payload = response.json()
    detections = payload.get("detections", [])
    if not detections:
        raise AssertionError("/api/scan returned no detections")
    first = detections[0]
    if first.get("kind") != "passport":
        raise AssertionError(f"expected passport detection, got {first!r}")
    if "text" in first:
        raise AssertionError("/api/scan detection includes forbidden text field")


def _assert_anonymize(base_url: str) -> None:
    response = _post_json(urljoin(base_url, "api/anonymize"), {"text": SAMPLE_TEXT})
    if response.status != 200:
        raise AssertionError(f"/api/anonymize returned {response.status}: {response.body}")
    if SAMPLE_PII in response.body:
        raise AssertionError("/api/anonymize echoed raw PII in the response body")

    payload = response.json()
    if payload.get("text") == SAMPLE_TEXT:
        raise AssertionError("/api/anonymize returned unmasked input")
    for detection in payload.get("detections", []):
        if "text" in detection:
            raise AssertionError("/api/anonymize detection includes forbidden text field")


def _assert_cors_rejects_untrusted_origin(base_url: str) -> None:
    response = _request(
        "OPTIONS",
        urljoin(base_url, "api/scan"),
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin")
    if allow_origin in {"*", "https://evil.example"}:
        raise AssertionError(f"untrusted CORS origin was allowed: {allow_origin}")


def _assert_rate_limit(base_url: str, attempts: int) -> None:
    if attempts < 2:
        raise AssertionError("--rate-limit-attempts must be at least 2")

    for _ in range(attempts):
        response = _post_json(urljoin(base_url, "api/scan"), {"text": "synthetic test sentence"})
        if response.status == 429:
            return
        if response.status >= 500:
            raise AssertionError(f"rate-limit probe hit server error: {response.status}")

    raise AssertionError(
        f"process-local rate limit was not observed within {attempts} attempts"
    )


def _post_json(url: str, payload: dict[str, Any]) -> Response:
    return _request(
        "POST",
        url,
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
    )


def _request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> Response:
    request = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=20) as raw:
            return _response_from_raw(raw)
    except HTTPError as exc:
        return Response(
            status=exc.code,
            headers={key.lower(): value for key, value in exc.headers.items()},
            body=exc.read().decode("utf-8", errors="replace"),
        )
    except URLError as exc:
        raise AssertionError(f"request failed for {url}: {exc}") from exc


def _response_from_raw(raw: HTTPResponse) -> Response:
    return Response(
        status=raw.status,
        headers={key.lower(): value for key, value in raw.headers.items()},
        body=raw.read().decode("utf-8", errors="replace"),
    )


if __name__ == "__main__":
    raise SystemExit(main())
