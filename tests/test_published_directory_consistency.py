"""Check authoritative catalog against the actual production build.

Source .html templates are allowed to contain older placeholder copy; build.py
regenerates the full public output from verified-directory.json.
"""
import json
import re
import subprocess
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_FILES = {
    "검색·포털": "search", "금융·경제": "finance",
    "교육·취업": "education", "생활·교통·여행": "travel",
    "쇼핑·가격비교": "shopping", "뉴스·언론": "news",
    "커뮤니티": "community", "AI 도구": "ai",
    "스포츠": "sports", "영상·OTT": "video",
    "만화·웹툰": "webtoon", "만화": "comics-directory",
    "한인교민": "korean",
}


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.current = None
        self.field = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "article" and any(x in a.get("class", "").split() for x in ("v6-card", "item")):
            self.current = {"name": "", "category": "", "description": "", "url": ""}
            self.items.append(self.current)
        elif self.current is not None:
            if tag in ("h3", "strong") and not self.current["name"]:
                self.field = "name"
            elif tag == "small" and not self.current["category"]:
                self.field = "category"
            elif tag == "p" and not self.current["description"]:
                self.field = "description"
            elif (tag == "a" and not self.current["url"]
                  and a.get("href", "").startswith("https://")):
                self.current["url"] = a["href"]

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None
            self.field = None
        elif tag in ("h3", "strong", "small", "p"):
            self.field = None

    def handle_data(self, data):
        if self.current is not None and self.field:
            self.current[self.field] += data


def cards(filename):
    parser = Cards()
    parser.feed(filename.read_text(encoding="utf-8"))
    return parser.items


class CatalogConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        fields = ("name", "url", "category", "description")
        cls.public_records = [{key: row[key] for key in fields} for row in cls.records]

    def test_catalog_has_unique_real_https_links_and_korean_first_order(self):
        from urllib.parse import urlsplit
        rows = self.records
        order = list(CATEGORY_FILES)
        self.assertGreaterEqual(len(rows), 200)
        self.assertEqual(len(rows), len({r["url"] for r in rows}))
        self.assertEqual(len(rows), len({r["name"] for r in rows}))
        self.assertEqual([order.index(r["category"]) for r in rows],
                         sorted(order.index(r["category"]) for r in rows))
        for row in rows:
            parsed = urlsplit(row["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.hostname)
            self.assertIsNone(parsed.username)
            self.assertIsNone(parsed.password)
            self.assertTrue(row["description"].strip())

    def test_production_directory_contains_every_verified_listing(self):
        path = ROOT / "dist/directory.html"
        if not path.exists():
            self.skipTest("build.py not run yet")
        self.assertEqual(cards(path), self.public_records)

    def test_production_categories_contain_all_verified_listings(self):
        if not (ROOT / "dist/directory.html").exists():
            self.skipTest("build.py not run yet")
        for category, slug in CATEGORY_FILES.items():
            with self.subTest(category=category):
                expected = [r for r in self.public_records if r["category"] == category]
                path = ROOT / "dist/categories" / (slug + ".html")
                self.assertTrue(path.exists(), slug)
                self.assertEqual(cards(path), expected)

    def test_visible_homepage_count_and_search_consistent_with_source(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"{len(self.records)}개 사이트 검색", html)
        if (ROOT / "dist/index.html").exists():
            built = (ROOT / "dist/index.html").read_text(encoding="utf-8")
            self.assertIn('action="/directory"', built)
            self.assertIn(f"{len(self.records)}개", built)

    def test_browser_search_uses_single_json_catalog_without_embedding_duplicate(self):
        js = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"const\s+sites\s*=\s*\[")
        self.assertIn("querySelectorAll('article.v6-card')", js)
        script = """
const fs = require('fs');
const search = require(process.argv[1]);
const rows = JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
for (const term of ['주소모음','링크모음','사이트모음']) {
  if (search.sortResults(rows,term).length !== rows.length) process.exit(1);
}
for (const name of ['네이버','정부24','Cursor','한국배구연맹 KOVO','쿠팡플레이']) {
  if (search.sortResults(rows,name)[0]?.name !== name) process.exit(2);
}
"""
        result = subprocess.run(["node", "-e", script,
                                 str(ROOT / "assets/directory-search.js"),
                                 str(ROOT / "assets/verified-directory.json")],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


    def test_current_count_in_search_guide_matches_catalog(self):
        guide = (ROOT / "content/seo-20261111-address-directory-no-results.md").read_text(encoding="utf-8")
        self.assertIn(f"2026년 11월 18일 현재 공개 전체 목록에는 {len(self.records)}개 사이트가 등록되어 있습니다.", guide)

    def test_official_announcement_evidence_type_is_supported(self):
        from build import DIRECTORY_EVIDENCE_TYPES
        self.assertIn("official_announcement", DIRECTORY_EVIDENCE_TYPES)

    def test_gemini_notebook_rebrand_is_consistent(self):
        row = next(item for item in self.records if item["url"] == "https://notebook.google.com/")
        self.assertEqual(row["name"], "Gemini Notebook (구 NotebookLM)")
        guide = (ROOT / "content/seo-20261110-korean-ai-tools-by-task-guide.md").read_text(encoding="utf-8")
        self.assertNotIn("[NotebookLM]", guide)
        self.assertIn("Gemini Notebook (구 NotebookLM)", guide)

    def test_korean_public_safety_services_have_official_evidence(self):
        expected = {
            "안전신문고": "https://www.safetyreport.go.kr/",
            "생활안전지도": "https://www.safemap.go.kr/",
        }
        evidence = json.loads((ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))
        evidence_by_url = {row["url"]: row for row in evidence}
        for name, url in expected.items():
            with self.subTest(name=name):
                row = next(item for item in self.records if item["name"] == name)
                self.assertEqual(row["url"], url)
                self.assertEqual(row["category"], "검색·포털")
                self.assertEqual(evidence_by_url[url]["evidence_type"], "service_page")
                self.assertTrue(evidence_by_url[url]["source_url"].startswith("https://www.mois.go.kr/"))

    def test_national_heritage_portal_has_official_evidence(self):
        row = next(item for item in self.records if item["name"] == "국가유산포털")
        self.assertEqual(row["url"], "https://www.heritage.go.kr/main/")
        self.assertEqual(row["category"], "생활·교통·여행")
        evidence = json.loads((ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))
        record = next(item for item in evidence if item["url"] == row["url"])
        self.assertEqual(record["evidence_type"], "service_page")
        self.assertEqual(record["source_url"], row["url"])
        self.assertIn("지역별 검색", record["scope"])

    def test_korean_public_utility_services_have_official_evidence(self):
        expected = {
            "금융상품 한눈에": {
                "url": "https://finlife.fss.or.kr/finlife/main/main.do?menuNo=700000",
                "category": "금융·경제",
                "source": "https://finlife.fss.or.kr/finlife/main/main.do?menuNo=700000",
            },
            "토지이음": {
                "url": "https://www.eum.go.kr/",
                "category": "생활·교통·여행",
                "source": "https://www.eum.go.kr/web/am/visit.jsp",
            },
            "우정사업본부": {
                "url": "https://www.koreapost.go.kr/kpost/index.do",
                "category": "생활·교통·여행",
                "source": "https://www.koreapost.go.kr/kpost/subIndex/4303.do?pSiteIdx=125",
            },
        }
        evidence = json.loads((ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))
        evidence_by_url = {row["url"]: row for row in evidence}
        for name, details in expected.items():
            with self.subTest(name=name):
                row = next(item for item in self.records if item["name"] == name)
                self.assertEqual(row["url"], details["url"])
                self.assertEqual(row["category"], details["category"])
                source = evidence_by_url[row["url"]]
                self.assertEqual(source["source_url"], details["source"])
                self.assertEqual(source["evidence_type"], "service_page")
                self.assertEqual(source["checked_on"], "2026-11-17")

    def test_korcham_secure_destination_keeps_existing_comparison_anchor(self):
        from build import directory_card_anchor

        records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        site = next(record for record in records if record["name"] == "대한상공회의소 코참넷")
        self.assertEqual(site["url"], "https://www.korcham.net/nCham/Service/Main/appl/Main.asp")
        self.assertEqual(directory_card_anchor(site),
                         directory_card_anchor({"url": "https://www.korcham.net/"}))


    def test_srt_listing_reflects_2026_rail_integration(self):
        row = next(item for item in self.records if item["name"] == "SRT")
        self.assertEqual(row["url"], "https://etk.srail.kr/")
        self.assertIn("2026년 9월 1일 이후 통합열차 승차권은 코레일+ 앱 또는 코레일 홈페이지", row["description"])
        evidence = json.loads((ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))
        record = next(item for item in evidence if item["url"] == row["url"])
        self.assertEqual(record["evidence_type"], "official_announcement")
        self.assertEqual(record["source_url"], "https://etk.srail.kr/cms/article/view.do?pageId=TK0502000000&pageIndex=31&postNo=922")
        self.assertIn("기존 SRT 홈페이지 예매 서비스는 종료", record["scope"])


if __name__ == "__main__":
    unittest.main()
