"""Indexed homepage serves real direct visit tasks, not just an SEO doorway."""
import json
from pathlib import Path
import unittest
from html.parser import HTMLParser

from build import CATEGORY_LANDING, homepage_directory_examples

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs))


class HomepageRealNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))

    def test_direct_links_are_exact_registered_urls_not_redirects_or_fabricated(self):
        html = homepage_directory_examples(self.records, CATEGORY_LANDING)
        parser = Links()
        parser.feed(html)
        published = {r["url"] for r in self.records}
        external = [link for link in parser.links
                    if link.get("href", "").startswith("https://")]
        self.assertEqual(len(external), sum(min(5, sum(row["category"] == category for row in self.records)) for category, _, _, _ in CATEGORY_LANDING))
        self.assertEqual(len({link["href"] for link in external}), len(external))
        for link in external:
            self.assertIn(link["href"], published)
            self.assertEqual(link["target"], "_blank")
            self.assertIn("noopener", link["rel"])
            self.assertIn("noreferrer", link["rel"])
            self.assertIn("external", link["rel"])
        self.assertIn('href="/directory"', html)
        self.assertIn("공식성·실시간 접속·안전성을 보증하지 않습니다", html)
        self.assertEqual(html.count('class="v6-card"'), len(CATEGORY_LANDING))

    def test_generated_indexed_homepage_contains_direct_links_before_guide(self):
        path = ROOT / "dist" / "index.html"
        if not path.exists():
            self.skipTest("Build first")
        html = path.read_text(encoding="utf-8")
        self.assertIn("관심 분야부터 찾기", html)
        self.assertIn("등록 사이트 새 창에서 열기", html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('href="https://linkwiki.info/" rel="canonical"', html)
        self.assertIn('action="/directory"', html)
        self.assertNotIn('id="directory-two-site-compare"', html)

    def test_homepage_exposes_every_category_and_the_full_link_hub(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        parser = Links()
        parser.feed(html)
        hrefs = {link.get("href") for link in parser.links}
        for _, slug, _, _ in CATEGORY_LANDING:
            with self.subTest(slug=slug):
                self.assertIn(f"categories/{slug}.html", hrefs)
        self.assertIn("categories/", hrefs)
        self.assertIn("directory.html", hrefs)

    def test_unsafe_data_does_not_enter_indexed_homepage(self):
        records = [dict(r) for r in self.records]
        first_category = CATEGORY_LANDING[0][0]
        first = next(r for r in records if r["category"] == first_category)
        first["url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(RuntimeError, "Invalid registered example URL"):
            homepage_directory_examples(records, CATEGORY_LANDING)


if __name__ == "__main__":
    unittest.main()
