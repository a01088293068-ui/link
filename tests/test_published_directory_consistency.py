"""Check authoritative catalog against the actual production build.

Source .html templates are allowed to contain older placeholder copy; build.py
regenerates the full 222-card public output from verified-directory.json.
"""
import json
import re
import subprocess
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_FILES = {
    "검색·포털": "search", "커뮤니티": "community",
    "AI 도구": "ai", "스포츠": "sports",
    "영상·OTT": "video", "만화·웹툰": "webtoon",
    "만화": "comics-directory", "한인교민": "korean",
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
            if tag in ("h3", "strong"):
                self.field = "name"
            elif tag == "small":
                self.field = "category"
            elif tag == "p":
                self.field = "description"
            elif tag == "a" and a.get("href", "").startswith("https://"):
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


    def test_korcham_secure_destination_keeps_existing_comparison_anchor(self):
        from build import directory_card_anchor

        records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        site = next(record for record in records if record["name"] == "대한상공회의소 코참넷")
        self.assertEqual(site["url"], "https://www.korcham.net/nCham/Service/Main/appl/Main.asp")
        self.assertEqual(directory_card_anchor(site),
                         directory_card_anchor({"url": "https://www.korcham.net/"}))


if __name__ == "__main__":
    unittest.main()
