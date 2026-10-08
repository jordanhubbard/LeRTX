import json
import unittest

from lertx.transport import (
    CancelToken,
    RateLimitedTransportError,
    TimeoutTransportError,
    TransportError,
    test_connection as probe_connection,
)


def _fake_transport(status, body_obj, headers=None):
    def _transport(url, headers_in, body, timeout):
        return status, headers or {}, json.dumps(body_obj).encode("utf-8")

    return _transport


class TransportTests(unittest.TestCase):
    def test_missing_key_never_calls_transport(self):
        calls = []

        def _transport(*args):
            calls.append(args)
            raise AssertionError("transport should not be called without an API key")

        result = probe_connection("https://x/y", "m", "", 10, 5, transport=_transport)
        self.assertEqual(result, {"state": "missing_key"})
        self.assertEqual(calls, [])

    def test_successful_text_access(self):
        body = {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "ok"}]}
            ],
        }
        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_fake_transport(200, body))
        self.assertEqual(result, {"state": "success"})

    def test_incomplete_response(self):
        body = {"status": "incomplete", "output": []}
        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_fake_transport(200, body))
        self.assertEqual(result, {"state": "incomplete"})

    def test_auth_failure(self):
        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_fake_transport(401, {}))
        self.assertEqual(result, {"state": "auth_failure"})

    def test_unknown_model(self):
        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_fake_transport(404, {}))
        self.assertEqual(result, {"state": "unknown_model"})

    def test_rate_limited_status_code(self):
        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_fake_transport(429, {}))
        self.assertEqual(result, {"state": "rate_limited"})

    def test_service_failure_on_bad_json(self):
        def _transport(url, headers, body, timeout):
            return 200, {}, b"not-json"

        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_transport)
        self.assertEqual(result, {"state": "service_failure"})

    def test_timeout_is_reported(self):
        def _transport(url, headers, body, timeout):
            raise TimeoutTransportError("timed out")

        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_transport)
        self.assertEqual(result, {"state": "timeout"})

    def test_rate_limited_exception_is_reported(self):
        def _transport(url, headers, body, timeout):
            raise RateLimitedTransportError("slow down")

        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_transport)
        self.assertEqual(result, {"state": "rate_limited"})

    def test_generic_transport_error_is_service_failure(self):
        def _transport(url, headers, body, timeout):
            raise TransportError("boom")

        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_transport)
        self.assertEqual(result, {"state": "service_failure"})

    def test_cancelled_after_response_is_reported(self):
        body = {"status": "completed", "output": []}
        token = CancelToken()
        token.cancel()
        result = probe_connection(
            "https://x/y", "m", "key", 10, 5, transport=_fake_transport(200, body), cancel_token=token
        )
        self.assertEqual(result, {"state": "cancelled"})

    def test_oversized_response_is_service_failure(self):
        def _transport(url, headers, body, timeout):
            return 200, {}, b"x" * (4 * 1024 * 1024 + 1)

        result = probe_connection("https://x/y", "m", "key", 10, 5, transport=_transport)
        self.assertEqual(result, {"state": "service_failure"})

    def test_never_leaks_api_key_in_result(self):
        body = {"status": "completed", "output": []}
        result = probe_connection(
            "https://x/y", "m", "top-secret-key", 10, 5, transport=_fake_transport(200, body)
        )
        self.assertNotIn("top-secret-key", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
