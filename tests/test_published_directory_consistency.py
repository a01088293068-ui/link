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

    def test_verified_korean_public_service_expansion_is_published_everywhere(self):
        expected = {
            "국민건강보험공단": "www.nhis.or.kr",
            "국민연금공단": "www.nps.or.kr",
            "국가건강정보포털": "health.kdca.go.kr",
            "건강보험심사평가원": "www.hira.or.kr",
            "국민신문고": "www.epeople.go.kr",
            "한국소비자원": "www.kca.go.kr",
            "국가전자도서관": "dlibrary.go.kr",
            "위택스": "www.wetax.go.kr",
            "식품안전나라": "www.foodsafetykorea.go.kr",
            "안전운전 통합민원": "www.safedriving.or.kr",
            "표준국어대사전": "stdict.korean.go.kr",
            "서울시 교통정보 TOPIS": "topis.seoul.go.kr",
            "K-Startup 창업지원포털": "www.k-startup.go.kr",
            "특허로": "www.patent.go.kr",
            "기업마당": "bizinfo.go.kr",
            "KIPRIS 지식재산정보검색": "www.kipris.or.kr",
            "관세청 유니패스": "unipass.customs.go.kr",
            "대한상공회의소 코참넷": "www.korcham.net",
        }
        by_name = {record["name"]: record for record in self.records}
        category_cards = cards(ROOT / "categories/search.html")
        directory_cards = cards(ROOT / "directory.html")
        for name, hostname in expected.items():
            with self.subTest(name=name):
                self.assertIn(name, by_name)
                self.assertEqual(urlsplit(by_name[name]["url"]).hostname, hostname)
                self.assertIn(by_name[name], category_cards)
                self.assertIn(by_name[name], directory_cards)
        self.assertEqual(len(self.records), len(directory_cards))
        self.assertEqual(
            len([record for record in self.records
                 if record["category"] == "검색·포털"]), len(category_cards))

    def test_actual_browser_search_engine_finds_new_korean_services(self):
        import shutil
        import subprocess
        if not shutil.which("node"):
            self.skipTest("Node.js is unavailable in this test environment")
        program = """
const fs = require('fs');
const search = require(process.argv[1]);
const rows = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const queries = [
  ['국민건강보험공단', '국민건강보험공단'],
  ['사이트모음 국민연금공단', '국민연금공단'],
  ['health.kdca.go.kr', '국가건강정보포털'],
  ['건강보험심사평가원', '건강보험심사평가원'],
  ['국민신문고', '국민신문고'],
  ['주소모음 한국소비자원', '한국소비자원'],
  ['국가전자도서관', '국가전자도서관'],
  ['지방세 위택스', '위택스'],
  ['식품안전나라', '식품안전나라'],
  ['안전운전 통합민원', '안전운전 통합민원'],
  ['표준국어대사전', '표준국어대사전'],
  ['서울시 교통정보 TOPIS', '서울시 교통정보 TOPIS'],
  ['주소모음·링크모음 국민신문고', '국민신문고'],
  ['링크모음, 위택스', '위택스'],
  ['주소모음|표준국어대사전', '표준국어대사전'],
  ['사이트모음 K-Startup 창업지원포털', 'K-Startup 창업지원포털'],
  ['특허로', '특허로'],
  ['기업마당', '기업마당'],
  ['KIPRIS 지식재산정보검색', 'KIPRIS 지식재산정보검색'],
  ['관세청 유니패스', '관세청 유니패스'],
  ['대한상공회의소 코참넷', '대한상공회의소 코참넷'],
];
for (const [query, expected] of queries) {
  const found = search.sortResults(rows, query);
  if (!found.length || found[0].name !== expected) {
    throw new Error(query + ' did not rank expected service first');
  }
}
if (search.sortResults(rows, '주소모음·링크모음·사이트모음').length !== rows.length) {
  throw new Error('punctuated directory intent excluded registered sites');
}
if (search.sortResults(rows, '주소모음').length !== rows.length) {
  throw new Error('generic address directory intent excluded registered sites');
}
if (search.sortResults(rows, '존재하지않는xyz123').length !== 0) {
  throw new Error('unmatched query returned unrelated records');
}
console.log('PASS: Korean directory queries and all-site intent');
"""
        result = subprocess.run(
            ["node", "-e", program, str(ROOT / "assets/directory-search.js"),
             str(ROOT / "assets/verified-directory.json")],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: Korean directory queries", result.stdout)

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
