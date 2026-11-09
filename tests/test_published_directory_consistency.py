"""Guard against drift between published LinkWiki directory sources.

Runs with stdlib only, without network, GSC tokens or a completed dist build.
"""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_FILES = {
    "검색·포털": "search",
    "영상·OTT": "video",
    "커뮤니티": "community",
    "한인교민": "korean",
    "만화": "comics-directory",
    "만화·웹툰": "webtoon",
    "스포츠": "sports",
    "AI 도구": "ai",
}


class CardParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.in_card = False
        self.depth = 0
        self.field = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = attrs.get("class", "").split()
        if tag == "article" and ("v6-card" in cls or "item" in cls):
            self.in_card = True
            self.depth = 1
            self.cards.append({"name": "", "category": "", "description": "", "url": ""})
            self.field = None
        elif self.in_card:
            if tag == "article":
                self.depth += 1
            if tag in ("h3", "strong"):
                self.field = "name"
            elif tag == "small":
                self.field = "category"
            elif tag == "p":
                self.field = "description"
            elif tag == "a" and attrs.get("href", "").startswith("https://"):
                self.cards[-1]["url"] = attrs["href"]

    def handle_data(self, data):
        if self.in_card and self.field:
            self.cards[-1][self.field] += data

    def handle_endtag(self, tag):
        if not self.in_card:
            return
        if tag in ("h3", "strong", "small", "p"):
            self.field = None
        if tag == "article":
            self.depth -= 1
            if self.depth == 0:
                self.in_card = False
                self.field = None


def cards(path):
    parser = CardParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.cards


class PublishedDirectoryConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(
            (ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))

    def test_valid_unique_https_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertEqual(len(self.records), len({x["name"] for x in self.records}))
        self.assertEqual(len(self.records), len({x["url"] for x in self.records}))
        for record in self.records:
            self.assertIn(record["category"], CATEGORY_FILES)
            self.assertTrue(record["name"].strip())
            self.assertTrue(record["description"].strip())
            url = urlsplit(record["url"])
            self.assertEqual(url.scheme, "https")
            self.assertTrue(url.hostname)
            self.assertIsNone(url.username)
            self.assertIsNone(url.password)

    def test_directory_javascript_matches_source_exactly(self):
        js = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        match = re.search(r"const sites=(\[.*?\]);\s*\(\(\)=>", js, flags=re.S)
        self.assertIsNotNone(match, "directory.js dataset not found")
        self.assertEqual(json.loads(match.group(1)), self.records)

    def test_static_directory_cards_match_published_data(self):
        self.assertEqual(cards(ROOT / "directory.html"), self.records)
        html = (ROOT / "directory.html").read_text(encoding="utf-8")
        self.assertIn(f"등록 사이트 {len(self.records)}개", html)

    def test_all_category_cards_match_source(self):
        for category, slug in CATEGORY_FILES.items():
            with self.subTest(category=category):
                expected = [r for r in self.records if r["category"] == category]
                path = ROOT / "categories" / f"{slug}.html"
                self.assertEqual(cards(path), expected)
                page = path.read_text(encoding="utf-8")
                if slug not in {"community", "korean", "comics-directory"}:
                    self.assertIn(f"{len(expected)}개 사이트 안내", page)


if __name__ == "__main__":
    unittest.main()
