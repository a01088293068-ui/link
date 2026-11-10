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
    def test_multiple_openwebside_listings_count_as_one_referring_domain(self):
        self.assertIn("OpenWebSide (older public listing)", monitor.SITES)
        rows = [
            {"url": monitor.SITES["OpenWebSide"], "state": "public_link_found"},
            {"url": monitor.SITES["OpenWebSide (older public listing)"],
             "state": "public_link_found"},
            {"url": monitor.SITES["SaaSKR"], "state": "public_link_found"},
            {"url": monitor.SITES["MeWebLink"], "state": "unverified"},
        ]
        self.assertEqual(monitor.distinct_referring_domains(rows),
                         ["openwebside.com", "saaskr.com"])
        for row in rows:
            row["name"] = "Existing public listing"
            row["detail"] = "read-only fixture"
        report = monitor.markdown(rows)
        self.assertIn("distinct referring domains in this HTTP sample: 2", report)
        self.assertIn("count once", report)

    def test_verified_korean_listing_is_monitored_as_existing_reference(self):
        self.assertEqual(
            monitor.SITES["VibeLabs Lab (self-authored listing)"],
            "https://vibelabs.kr/lab/projects/238")
        self.assertEqual(len(set(monitor.SITES.values())), len(monitor.SITES))
        html = (b'<html><meta name="robots" content="index, follow">'
                b'<a href="https://linkwiki.info/" rel="noopener noreferrer">'
                b'LinkWiki</a></html>')
        row = monitor.check_one(
            "VibeLabs", monitor.SITES["VibeLabs Lab (self-authored listing)"],
            lambda url: (200, url, html))
        self.assertEqual(row["state"], "public_link_found")
        self.assertIn("meta_noindex=False", row["detail"])

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
