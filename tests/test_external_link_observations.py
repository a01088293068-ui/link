"""Tests for cautious link health observations, URL allowlist and rotation."""
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("outbound_check", ROOT / "seo" / "observe_external_links.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class Response:
    def __init__(self, code=200):
        self.status = code
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Opener:
    def __init__(self, answer):
        self.answer = answer
        self.requests = []
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if isinstance(self.answer, Exception):
            raise self.answer
        return Response(self.answer)


class LinkObservationsTests(unittest.TestCase):
    def test_real_catalog_has_315_unique_public_https_targets(self):
        records = check.catalog_entries()
        self.assertGreaterEqual(len(records), 315)
        self.assertEqual(len({r["url"] for r in records}), len(records))
        self.assertTrue(all(check.safe_target(r["url"]) for r in records))

    def test_block_local_private_and_insecure_urls(self):
        for url in [
            "http://example.com/", "https://localhost/", "https://127.0.0.1/",
            "https://10.0.0.5/", "https://[::1]/", "https://foo.internal/",
            "https://metadata.google.internal/", "https://foo.local/",
            "https://user:secret@example.com/", "https://example.com:8443/",
            "https://example.com/#fragment", "javascript:alert(1)",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                check.safe_target(url)

    def test_rotation_covers_all_entries_in_dynamic_windows_without_repeats(self):
        entries = check.catalog_entries()
        day = date(2026, 11, 11)
        observed = []
        windows = (len(entries) + 23) // 24
        for index in range(windows):
            selected = check.select_batch(entries, day + timedelta(days=index))
            expected = min(24, len(entries) - index * 24)
            self.assertEqual(len(selected), expected)
            self.assertEqual(len({x["url"] for x in selected}), expected)
            observed += [x["url"] for x in selected]
        self.assertEqual(len(observed), len(entries))
        self.assertEqual(len(set(observed)), len(entries))

    def test_head_only_no_request_body_and_no_redirect_following(self):
        opener = Opener(200)
        result = check.check_url("https://www.naver.com/", opener=opener)
        self.assertEqual(result, {"status": "http_responded", "http_code": 200})
        self.assertEqual(opener.requests[0][0].get_method(), "HEAD")
        self.assertEqual(opener.requests[0][0].data, None)
        no_redirect = check.NoRedirect()
        self.assertIsNone(no_redirect.redirect_request(None, None, 302, "found", {}, "https://evil.example/"))

    def test_ambiguous_restricted_and_redirect_are_not_marked_dead(self):
        cases = [(302, "redirect_review"), (403, "access_limited"),
                 (405, "network_uncertain"), (429, "access_limited"),
                 (404, "http_error_review"), (503, "http_error_review")]
        for status, expected in cases:
            with self.subTest(status=status):
                err = HTTPError("https://www.naver.com/", status, "status", {}, None)
                result = check.check_url("https://www.naver.com/", opener=Opener(err))
                self.assertEqual(result["status"], expected)

    def test_timeout_is_uncertain_not_fake_verified_result(self):
        observed = check.check_url("https://www.naver.com/", opener=Opener(URLError("timeout")))
        self.assertEqual(observed["status"], "network_uncertain")
        self.assertNotIn("verified", json.dumps(observed))

    def test_report_preserves_real_names_and_never_changes_catalog(self):
        entries = check.catalog_entries()
        result = check.run(date(2026, 11, 11), entries, batch_size=2,
                           observer=lambda url: {"status": "network_uncertain"})
        self.assertEqual(result["checked_count"], 2)
        self.assertEqual(result["catalog_count"], len(records))
        self.assertEqual(result["results"][0]["name"], entries[0]["name"])
        self.assertIn("Never automatically delete", result["disclaimer"])
        self.assertEqual(len(entries), len(records))

    def test_json_catalog_validation_rejects_duplicate(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.json"
            path.write_text(json.dumps([
                {"name": "one", "url": "https://example.org/", "category": "검색·포털"},
                {"name": "two", "url": "https://example.org/", "category": "검색·포털"}
            ]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate catalog"):
                check.catalog_entries(path)


if __name__ == "__main__":
    unittest.main()
