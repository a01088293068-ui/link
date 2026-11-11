"""Offline tests for directory-intent index inspection coverage and triage."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from seo import search_console_monitor as monitor
from seo import index_priority_plan


class DirectoryIntentGoogleEvidenceTests(unittest.TestCase):
    def test_only_existing_published_guides_are_inspection_targets(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            posts = root / "content"
            posts.mkdir()
            slugs = monitor.DIRECTORY_INTENT_ARTICLES
            (posts / (slugs[0] + ".md")).write_text("# one", encoding="utf-8")
            (posts / (slugs[2] + ".md")).write_text("# two", encoding="utf-8")
            with patch.object(monitor, "ROOT", root):
                urls = monitor.directory_intent_inspection_urls()
                targets = monitor.inspection_targets([], limit=20)
            self.assertEqual(urls, [
                "https://linkwiki.info/blog/" + slugs[0] + "/",
                "https://linkwiki.info/blog/" + slugs[2] + "/",
            ])
            for url in urls:
                self.assertIn(url, targets)
            self.assertNotIn("https://linkwiki.info/blog/" + slugs[1] + "/", targets)

    def test_exact_google_query_landing_precedes_new_guide_candidates(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            posts = root / "content"
            posts.mkdir()
            for slug in monitor.DIRECTORY_INTENT_ARTICLES:
                (posts / (slug + ".md")).write_text("# guide", encoding="utf-8")
            row = [{"keys": ["주소모음", "https://linkwiki.info/guides/choose-directory"],
                    "impressions": 18, "clicks": 1}]
            with patch.object(monitor, "ROOT", root):
                targets = monitor.inspection_targets([], limit=17, core_query_pages=row)
            self.assertEqual(len(targets), 17)
            self.assertIn("https://linkwiki.info/guides/choose-directory", targets)
            self.assertEqual(len(targets), len(set(targets)))
            self.assertLess(targets.index("https://linkwiki.info/guides/choose-directory"),
                            targets.index("https://linkwiki.info/blog/" +
                                          monitor.DIRECTORY_INTENT_ARTICLES[0] + "/"))

    def test_inspected_blog_guides_are_reported_without_fake_rank(self):
        url = "https://linkwiki.info/blog/seo-20261111-address-directory-no-results/"
        snapshot = {"schema": 1, "end_date": "2026-11-10",
                    "inspections": [{"url": url, "verdict": "NEUTRAL",
                                     "coverage": "Crawled - currently not indexed",
                                     "last_crawl": "2026-11-07T08:00:00Z"}]}
        report = index_priority_plan.render(snapshot)
        article = report.split("## 핵심 가이드의 Google 저장 색인 상태")[1].split(
            "## Google 저장본 Canonical 차이")[0]
        self.assertIn(url, article)
        self.assertIn("크롤링 후 미색인", article)
        self.assertIn("독립적인 검색 목적", article)
        self.assertNotIn("1위", article)
        self.assertNotIn("검색 순위 상승", article)

    def test_noninspected_or_offsite_articles_not_reported(self):
        result = index_priority_plan.render({
            "schema": 1,
            "inspections": [
                {"url": "https://outside.example/blog/example/", "coverage": "Indexed"},
                {"url": "https://linkwiki.info/blog/other/", "verdict": "PASS"},
            ],
        })
        section = result.split("## 핵심 가이드의 Google 저장 색인 상태")[1].split(
            "## Google 저장본 Canonical 차이")[0]
        self.assertIn("https://linkwiki.info/blog/other/", section)
        self.assertNotIn("outside.example", section)


if __name__ == "__main__":
    unittest.main()
