"""Homepage and full directory must serve different search tasks without duplication."""
import json
from pathlib import Path
import re
import unittest

from build import CATEGORY_LANDING, homepage_directory_examples

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "verified-directory.json"


class DistinctHomeDirectoryIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(DATA.read_text(encoding="utf-8"))

    def test_homepage_overview_uses_names_and_purposes_not_full_site_records(self):
        overview = homepage_directory_examples(self.records, CATEGORY_LANDING)
        self.assertIn("관심 분야부터 찾기", overview)
        self.assertIn('href="/directory">전체 주소모음 목록', overview)
        self.assertIn("도메인·상세 설명·검색·직접 비교", overview)
        self.assertEqual(overview.count('<article class="v6-card">'), len(CATEGORY_LANDING))
        self.assertEqual(overview.count("등록 예시:"), len(CATEGORY_LANDING))
        for category, slug, heading, purpose in CATEGORY_LANDING:
            with self.subTest(slug=slug):
                entries = [x for x in self.records if x["category"] == category]
                self.assertTrue(entries)
                self.assertIn(entries[0]["name"], overview)
                self.assertIn(purpose, overview)
                self.assertIn(f'href="/categories/{slug}"', overview)
                # Do not reproduce per-site summaries or hosts on homepage.
                self.assertNotIn(entries[0]["description"], overview)
                self.assertNotIn("등록 도메인: " + entries[0]["url"], overview)

    def test_full_directory_is_the_sole_all_records_details_page(self):
        self.assertEqual(len(self.records), 228)
        path = ROOT / "dist" / "directory.html"
        home = ROOT / "dist" / "index.html"
        if not path.exists() or not home.exists():
            self.skipTest("Run build.py first")
        full = path.read_text(encoding="utf-8")
        hub = home.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'<article class="v6-card" id="site-[a-f0-9]{14}"', full)), len(self.records))
        self.assertEqual(hub.count("분야별 사이트 탐색 길잡이"), 1)
        self.assertIn("관심 분야부터 찾기", hub)
        self.assertIn('id="directory-two-site-compare"', full)
        self.assertNotIn('id="directory-two-site-compare"', hub)
        self.assertNotIn('class="home-example-names">등록 도메인', hub)
        self.assertIn('action="/directory"', hub)
        self.assertIn('rel="canonical"', hub)

    def test_no_made_up_names_or_unverified_safety_claims(self):
        overview = homepage_directory_examples(self.records, CATEGORY_LANDING)
        self.assertNotIn("검증 완료", overview)
        self.assertNotIn("실시간 접속 확인", overview)
        self.assertNotIn("1위", overview)
        for item in self.records:
            if item["name"] in overview:
                self.assertTrue(item["url"].startswith("https://"))

    def test_missing_category_and_insecure_example_fails_before_publish(self):
        category = CATEGORY_LANDING[0][0]
        absent = [x for x in self.records if x["category"] != category]
        with self.assertRaisesRegex(RuntimeError, "Missing descriptive directory example"):
            homepage_directory_examples(absent, CATEGORY_LANDING)
        corrupted = [dict(x) for x in self.records]
        first = next(x for x in corrupted if x["category"] == category)
        first["url"] = "http://fake.invalid/"
        with self.assertRaisesRegex(RuntimeError, "Invalid registered example URL"):
            homepage_directory_examples(corrupted, CATEGORY_LANDING)


if __name__ == "__main__":
    unittest.main()
