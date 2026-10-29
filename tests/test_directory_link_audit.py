"""Regression tests for public directory destination checks (no live requests)."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SCRIPT = Path(__file__).resolve().parents[1] / "seo" / "check_directory_links.py"
spec = importlib.util.spec_from_file_location("directory_link_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Response:
    def __init__(self, url, status=200):
        self.url = url
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


class DirectoryLinkAuditTests(unittest.TestCase):
    def setUp(self):
        self.record = {"name": "예시", "url": "https://example.org/path"}

    def test_ordinary_https_destination_remains_ok(self):
        with patch.object(audit, "urlopen", return_value=Response("https://example.org/new")):
            result = audit.check(self.record)
        self.assertEqual(result["result"], "ok")
        self.assertNotIn("redirect_warning", result)

    def test_cross_host_redirect_requires_review(self):
        with patch.object(audit, "urlopen", return_value=Response("https://other.example/home")):
            result = audit.check(self.record)
        self.assertEqual(result["result"], "needs_review")
        self.assertEqual(result["redirect_warning"], "destination_hostname_changed")

    def test_https_downgrade_requires_review(self):
        with patch.object(audit, "urlopen", return_value=Response("http://example.org/path")):
            result = audit.check(self.record)
        self.assertEqual(result["result"], "needs_review")
        self.assertEqual(result["security_warning"], "https_downgrade")

    def test_bot_restricted_is_not_called_dead(self):
        error = HTTPError("https://example.org/path", 403, "Forbidden", None, None)
        with patch.object(audit, "urlopen", side_effect=error):
            result = audit.check(self.record)
        self.assertEqual(result["result"], "access_restricted")

    def test_missing_url_is_separate_from_redirect_alert(self):
        error = HTTPError("https://example.org/path", 404, "Not Found", None, None)
        with patch.object(audit, "urlopen", side_effect=error):
            result = audit.check(self.record)
        self.assertEqual(result["result"], "not_found")


if __name__ == "__main__":
    unittest.main()
