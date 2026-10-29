from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from seo.check_directory_links import check, run


class DirectoryReachabilityTests(TestCase):
    def setUp(self):
        self.record = {"name": "테스트", "url": "https://example.com/"}

    def test_successful_redirect_resolves_destination(self):
        class Response:
            status = 200
            url = "https://example.com/new"
            def __enter__(self): return self
            def __exit__(self, *args): return None
        with patch("seo.check_directory_links.urlopen", return_value=Response()):
            row = check(self.record)
        self.assertEqual(row["result"], "ok")
        self.assertEqual(row["final_url"], "https://example.com/new")

    def test_blocked_bot_is_not_called_dead(self):
        error = HTTPError(self.record["url"], 403, "Forbidden", {}, None)
        with patch("seo.check_directory_links.urlopen", side_effect=error):
            row = check(self.record)
        self.assertEqual(row["result"], "access_restricted")

    def test_404_is_reviewable_not_deleted(self):
        error = HTTPError(self.record["url"], 404, "Not found", {}, None)
        with patch("seo.check_directory_links.urlopen", side_effect=error):
            row = check(self.record)
        self.assertEqual(row["result"], "not_found")

    def test_network_error_is_classified(self):
        with patch("seo.check_directory_links.urlopen", side_effect=URLError("offline")):
            row = check(self.record)
        self.assertEqual(row["result"], "unreachable")

    def test_run_preserves_input_order(self):
        records = [self.record, {"name": "둘째", "url": "https://example.org/"}]
        with patch("seo.check_directory_links.check", side_effect=lambda r, t: {"name": r["name"], "result": "ok"}):
            rows = run(records, workers=2)
        self.assertEqual([r["name"] for r in rows], ["테스트", "둘째"])
