"""Regression tests for transient, read-only Google Search Analytics retries."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import importlib.util
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "seo/search_console_monitor.py"
spec = importlib.util.spec_from_file_location("monitor_retry_test", SOURCE)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class Response:
    def __init__(self, data=b'{"rows":[{"keys":["주소모음"],"clicks":2}]}'):
        self.data = data
    def __enter__(self):
        return BytesIO(self.data)
    def __exit__(self, *args):
        return None


def search():
    return monitor.query_performance(
        "fake-token", "sc-domain:linkwiki.info",
        "2026-11-01", "2026-11-08", ["query"]
    )


class SearchAnalyticsRetryTests(unittest.TestCase):
    def test_transient_timeout_then_success(self):
        with patch.object(monitor, "urlopen",
                          side_effect=[TimeoutError("read timed out"), Response()]) as get, \
             patch.object(monitor.time, "sleep") as pause:
            rows = search()
        self.assertEqual(rows[0]["clicks"], 2)
        self.assertEqual(get.call_count, 2)
        pause.assert_called_once_with(2)

    def test_retry_429_and_503_with_bounded_backoff(self):
        fail = lambda code: HTTPError("https://www.googleapis.com", code, "retry", {}, None)
        with patch.object(monitor, "urlopen",
                          side_effect=[fail(429), fail(503), Response()]) as get, \
             patch.object(monitor.time, "sleep") as pause:
            self.assertEqual(search()[0]["clicks"], 2)
        self.assertEqual(get.call_count, 3)
        self.assertEqual([x.args[0] for x in pause.call_args_list], [2, 4])

    def test_permission_error_never_retried(self):
        err = HTTPError("https://www.googleapis.com", 403, "forbidden", {}, None)
        with patch.object(monitor, "urlopen", side_effect=err) as get, \
             patch.object(monitor.time, "sleep") as pause:
            with self.assertRaises(HTTPError):
                search()
        get.assert_called_once()
        pause.assert_not_called()

    def test_persistent_timeout_exits_after_three_attempts(self):
        with patch.object(monitor, "urlopen", side_effect=TimeoutError("timeout")) as get, \
             patch.object(monitor.time, "sleep") as pause:
            with self.assertRaises(TimeoutError):
                search()
        self.assertEqual(get.call_count, 3)
        self.assertEqual([x.args[0] for x in pause.call_args_list], [2, 4])

    def test_transient_network_error_retried(self):
        with patch.object(monitor, "urlopen",
                          side_effect=[URLError("connection reset"), Response()]) as get, \
             patch.object(monitor.time, "sleep"):
            self.assertEqual(len(search()), 1)
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
