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

    def test_homepage_exposes_real_source_evidence_with_scope_caveat(self):
        import build
        summary = build.homepage_evidence_summary(self.records)
        evidence = build.load_directory_evidence(self.records)
        self.assertIn(f"공개 목록 {len(self.records)}개 가운데 {len(evidence)}건의 출처 대조 기록", summary)
        self.assertIn('href="/directory#directory-source-evidence"', summary)
        self.assertIn('href="/guides/directory-maintenance"', summary)
        self.assertIn("실시간 접속 확인이나 공식 인증 비율을 뜻하지 않습니다", summary)
        self.assertNotIn("전체 사이트 검증 완료", summary)

    def test_homepage_owns_head_terms_while_directory_owns_name_domain_search(self):
        import build
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        directory = (ROOT / "directory.html").read_text(encoding="utf-8")
        rendered = build.sync_directory_count(directory, len(self.records))
        home_title = re.search(r"<title>(.*?)</title>", home, re.S).group(1)
        directory_title = re.search(r"<title>(.*?)</title>", rendered, re.S).group(1)
        directory_heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", rendered, re.S).group(1)
        self.assertTrue(all(term in home_title for term in ("주소모음", "링크모음", "사이트모음")))
        self.assertIn("사이트모음 전체 목록", directory_title)
        self.assertIn("검색·비교", directory_title)
        self.assertTrue(all(term not in directory_title for term in ("주소모음", "링크모음")))
        self.assertIn("사이트모음 전체 목록", directory_heading)
        self.assertIn("이름·도메인 검색", directory_heading)
        self.assertTrue(all(term not in directory_heading for term in ("주소모음", "링크모음")))
        self.assertIn(f"{len(self.records)}개", directory_heading)
        description = re.search(r'<meta\b(?=[^>]*\bname="description")(?=[^>]*\bcontent="([^"]*)")[^>]*>', rendered, re.S).group(1)
        self.assertIn(f"{len(self.records)}개 등록 사이트", description)
        self.assertIn("연결 주소를 비교", description)
        self.assertIn("사이트모음 전체 목록", re.search(r'<meta\b(?=[^>]*\bproperty="og:title")(?=[^>]*\bcontent="([^"]*)")[^>]*>', rendered, re.S).group(1))

    def test_full_directory_is_the_sole_all_records_details_page(self):
        self.assertGreaterEqual(len(self.records), 315)
        path = ROOT / "dist" / "directory.html"
        home = ROOT / "dist" / "index.html"
        if not path.exists() or not home.exists():
            self.skipTest("Run build.py first")
        full = path.read_text(encoding="utf-8")
        hub = home.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'<article class="v6-card" data-source-evidence="(?:true|false)" id="site-[a-f0-9]{14}"', full)), len(self.records))
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
