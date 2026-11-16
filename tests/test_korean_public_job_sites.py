import json
import re
import unittest
from pathlib import Path

from seo import search_console_monitor

ROOT = Path(__file__).resolve().parents[1]
SLUG = "seo-20261116-korean-public-sector-recruitment-sites-guide"
EXPECTED = {
    "나라일터": "https://www.gojobs.go.kr/mainIndex.do",
    "잡알리오": "https://job.alio.go.kr/main.do",
    "클린아이 잡플러스": "https://job.cleaneye.go.kr/",
}


class KoreanPublicJobSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(
            (ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.evidence = json.loads(
            (ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))
        cls.article = (ROOT / "content" / (SLUG + ".md")).read_text(encoding="utf-8")

    def test_three_official_public_recruitment_services_are_distinct_catalog_entries(self):
        by_name = {row["name"]: row for row in self.records}
        for name, url in EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["url"], url)
                self.assertEqual(by_name[name]["category"], "교육·취업")
                self.assertGreaterEqual(len(by_name[name]["description"]), 50)
        self.assertEqual(len({row["url"] for row in self.records}), len(self.records))
        self.assertEqual(len({row["name"] for row in self.records}), len(self.records))

    def test_each_new_listing_has_official_service_evidence(self):
        by_url = {row["url"]: row for row in self.evidence}
        for name, url in EXPECTED.items():
            with self.subTest(name=name):
                item = by_url[url]
                self.assertEqual(item["name"], name)
                self.assertEqual(item["evidence_type"], "service_page")
                self.assertEqual(item["checked_on"], "2026-11-16")
                self.assertTrue(item["source_url"].startswith("https://"))

    def test_article_explains_distinct_recruitment_scopes_and_links_official_sources(self):
        for phrase in ("국가기관·지자체·교육청", "중앙 공공기관", "지방공기업",
                       "지역 제한", "접수 마감 시각", "최종 접수 완료"):
            self.assertIn(phrase, self.article)
        for url in EXPECTED.values():
            self.assertIn(url, self.article)
        self.assertIn("/categories/education", self.article)
        self.assertIn("/directory", self.article)

    def test_new_guide_is_in_daily_inspection_and_korean_query_reporting(self):
        url = "https://linkwiki.info/blog/" + SLUG + "/"
        self.assertIn(url, search_console_monitor.directory_intent_inspection_urls())
        self.assertIn(("공공기관·지방공기업 채용", SLUG),
                      search_console_monitor.LONG_TAIL_GUIDES)
        expression = search_console_monitor.korea_guide_query_filters()[0]["filters"][1]["expression"]
        self.assertIsNotNone(re.fullmatch(expression, url))
        self.assertIsNone(re.fullmatch(expression, url + "?utm_source=test"))


if __name__ == "__main__":
    unittest.main()
