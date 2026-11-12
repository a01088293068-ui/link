"""Public backlink checker must find canonical /directory citations as well as home."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("linkwiki_public_backlinks", ROOT / "seo" / "backlink-public-check.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class DirectoryBacklinkEvidenceTests(unittest.TestCase):
    def run_check(self, body):
        return checker.check_one(
            "Outside service", "https://directory.example.test/my-listing",
            lambda url: (200, url, body.encode("utf-8"))
        )

    def test_homepage_and_directory_are_distinct_real_targets(self):
        html = ('<a href="https://linkwiki.info/">홈페이지</a>'
                '<a href="https://linkwiki.info/directory">전체 목록</a>')
        result = self.run_check(html)
        self.assertEqual(result["state"], "public_link_found")
        self.assertEqual(result["targets"], ["/", "/directory"])
        self.assertIn("2 direct href(s)", result["detail"])

    def test_only_directory_link_counts_and_shows_destination(self):
        result = self.run_check(
            '<meta name="robots" content="index,follow">'
            '<a href="https://linkwiki.info/directory" rel="ugc">주소모음</a>')
        self.assertEqual(result["state"], "public_link_found")
        self.assertEqual(result["targets"], ["/directory"])
        self.assertIn("ugc", result["detail"])
        self.assertIn("/directory", checker.markdown([result]))

    def test_legacy_uncanonical_and_fake_host_excluded(self):
        for href in (
            "https://linkwiki.info/directory.html",
            "https://linkwiki.info.bad-domain.example/directory",
            "http://linkwiki.info/directory",
            "https://user:password@linkwiki.info/directory",
            "https://linkwiki.info:8443/directory",
            "https://blog.linkwiki.info/directory",
        ):
            with self.subTest(href=href):
                self.assertEqual(
                    self.run_check(f'<a href="{href}">URL</a>')["state"],
                    "no_direct_link")

    def test_same_external_domain_multiple_links_count_once(self):
        entries = [
            {"url": "https://place.example.com/list/a",
             "state": "public_link_found", "targets": ["/"]},
            {"url": "https://place.example.com/list/b",
             "state": "public_link_found", "targets": ["/directory"]},
            {"url": "https://another.example.com/entry",
             "state": "unverified", "targets": []},
        ]
        self.assertEqual(checker.distinct_referring_domains(entries),
                         ["place.example.com"])
        for entry in entries:
            entry["name"] = "External link"
            entry["detail"] = "read-only fixture"
        report = checker.markdown(entries)
        self.assertIn("distinct referring domains in this HTTP sample: 1", report)
        self.assertIn("Target pages", report)

    def test_query_string_never_makes_offsite_host_valid(self):
        result = self.run_check(
            '<a href="https://linkwiki.info.evil.test/?to=linkwiki.info/directory">Fake</a>')
        self.assertEqual(result["state"], "no_direct_link")


if __name__ == "__main__":
    unittest.main()
