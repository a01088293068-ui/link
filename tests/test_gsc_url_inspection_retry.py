"""Bounded retry coverage for transient Google URL Inspection transport failures."""
import io
import json
from pathlib import Path
import importlib.util
from unittest.mock import patch
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "gsc_inspection_retry_test", ROOT / "seo" / "search_console_monitor.py"
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class FakeResponse:
    def __init__(self, payload):
        self.stream = io.StringIO(json.dumps(payload))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return self.stream.read(*args)


class InspectionRetryTests(unittest.TestCase):
    def test_transient_timeout_retries_once_and_returns_homepage_evidence(self):
        payload = {"inspectionResult": {"indexStatusResult": {
            "verdict": "PASS",
            "coverageState": "제출되고 색인이 생성되었습니다.",
            "lastCrawlTime": "2026-11-18T02:14:26Z",
        }}}
        with patch.object(monitor, "urlopen", side_effect=[TimeoutError(), FakeResponse(payload)]) as mocked:
            result = monitor.inspect_index("token", "sc-domain:linkwiki.info", "https://linkwiki.info/")
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["last_crawl"], "2026-11-18T02:14:26Z")
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual([call.kwargs["timeout"] for call in mocked.call_args_list], [8, 8])

    def test_http_error_is_not_retried(self):
        error = HTTPError("https://example.com", 403, "forbidden", {}, None)
        with patch.object(monitor, "urlopen", side_effect=error) as mocked:
            with self.assertRaises(HTTPError):
                monitor.inspect_index("token", "sc-domain:linkwiki.info", "https://linkwiki.info/")
        self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
