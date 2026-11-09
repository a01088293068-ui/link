"""Offline regression tests for public citation monitor (no network calls)."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "seo/backlink-public-check.py"
SPEC = importlib.util.spec_from_file_location("backlink_public_check", PATH)
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


class BacklinkPublicCheckTests(unittest.TestCase):
    URL = "https://example-directory.test/linkwiki"
    def test_direct_anchor_counts(self):
        html = b'<html><meta name="robots" content="index, follow"><a href="https://linkwiki.info/" rel="ugc nofollow">Visit</a></html>'
        row = monitor.check_one("test", self.URL, lambda _: (200, self.URL, html))
        self.assertEqual(row["state"], "public_link_found")
        self.assertIn("ugc nofollow", row["detail"])

    def test_plain_domain_text_does_not_count_as_link(self):
        html = b'<html><p>linkwiki.info</p><a href="https://different.test/">Other</a></html>'
        row = monitor.check_one("test", self.URL, lambda _: (200, self.URL, html))
        self.assertEqual(row["state"], "no_direct_link")

    def test_other_domain_lookalike_does_not_count(self):
        html = b'<a href="https://linkwiki.info.bad-domain.test/">Bad</a>'
        row = monitor.check_one("test", self.URL, lambda _: (200, self.URL, html))
        self.assertEqual(row["state"], "no_direct_link")

    def test_http_failure_inconclusive(self):
        row = monitor.check_one("test", self.URL, lambda _: (404, self.URL, b""))
        self.assertEqual(row["state"], "unverified")

    def test_relative_href_is_not_target_domain(self):
        html = b'<a href="/directory">LinkWiki</a>'
        row = monitor.check_one("test", self.URL, lambda _: (200, self.URL, html))
        self.assertEqual(row["state"], "no_direct_link")


if __name__ == "__main__":
    unittest.main()
