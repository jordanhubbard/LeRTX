"""Bounded LLM connection testing.

The default transport uses only the standard library. Tests inject a
bounded fake transport carrying no live credentials.
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Callable, Optional

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_TEST_PROMPT = "Connection test from LeRTX."


class TransportError(Exception):
    """A transport-level failure that is not a specific classified state."""


class TimeoutTransportError(TransportError):
    pass


class RateLimitedTransportError(TransportError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        raise TransportError(f"redirect rejected (HTTP {code})")


def default_transport(url: str, headers: dict, body: bytes, timeout_seconds: int):
    """Perform the real bounded HTTPS POST. Returns (status, headers, body_bytes)."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        response = opener.open(request, timeout=timeout_seconds)
    except socket.timeout as exc:
        raise TimeoutTransportError(str(exc)) from exc
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        return status, dict(exc.headers or {}), raw
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise TimeoutTransportError(str(exc)) from exc
        raise TransportError(str(exc)) from exc
    with response:
        status = response.status
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        return status, dict(response.headers or {}), raw


def _extract_output_text(payload: dict) -> Optional[str]:
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    texts = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "output_text":
                text_value = block.get("text")
                if isinstance(text_value, str):
                    texts.append(text_value)
    if not texts:
        return None
    return "".join(texts)


class CancelToken:
    """A simple cooperative cancellation flag for asynchronous test requests."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled


def test_connection(
    endpoint: str,
    model: str,
    api_key: str,
    max_output_tokens: int,
    timeout_seconds: int,
    transport: Callable[[str, dict, bytes, int], Any] = default_transport,
    cancel_token: Optional[CancelToken] = None,
) -> dict:
    """Test connectivity to the configured LLM endpoint.

    Returns ``{"state": <state>}`` where state is one of: ``missing_key``,
    ``success``, ``incomplete``, ``auth_failure``, ``unknown_model``,
    ``timeout``, ``rate_limited``, ``service_failure``, ``cancelled``.
    Never includes the raw response body or any secret-bearing detail.
    """
    if not api_key:
        return {"state": "missing_key"}

    body = json.dumps(
        {"model": model, "input": _TEST_PROMPT, "max_output_tokens": max_output_tokens}
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        status, _resp_headers, resp_body = transport(endpoint, headers, body, timeout_seconds)
    except TimeoutTransportError:
        return {"state": "timeout"}
    except RateLimitedTransportError:
        return {"state": "rate_limited"}
    except TransportError:
        return {"state": "service_failure"}

    if cancel_token is not None and cancel_token.is_cancelled():
        return {"state": "cancelled"}

    if resp_body is None or len(resp_body) > MAX_RESPONSE_BYTES:
        return {"state": "service_failure"}
    if status in (401, 403):
        return {"state": "auth_failure"}
    if status == 404:
        return {"state": "unknown_model"}
    if status == 429:
        return {"state": "rate_limited"}
    if status != 200:
        return {"state": "service_failure"}

    try:
        payload = json.loads(resp_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {"state": "service_failure"}
    if not isinstance(payload, dict):
        return {"state": "service_failure"}

    payload_status = payload.get("status")
    if payload_status == "incomplete":
        return {"state": "incomplete"}
    if payload_status != "completed":
        return {"state": "service_failure"}

    text = _extract_output_text(payload)
    if text is None:
        return {"state": "service_failure"}
    return {"state": "success"}
