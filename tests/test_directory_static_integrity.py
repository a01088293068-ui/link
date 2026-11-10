"""Verify the 211 indexable static cards are the single source of browser search."""
import json
import re
import unittest
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = re.compile(
    r'<article class="v6-card"><small>(.*?)</small><h3>(.*?)</h3>'
    r'<p>(.*?)</p><span class="site-domain">.*?</span>'
    r'<a\\b[^>]*href="([^"]+)"',
    re.S,
)


class DirectoryCardTests(unittest.TestCase):
    def test_static_cards_match_all_verified_records(self):
        records = json.loads((ROOT / "assets/verified-directory.json").read_text(
            encoding="utf-8"))
        html = (ROOT / "dist/directory.html").read_text(encoding="utf-8")
        fragment = html.split('id="v6-results">', 1)[1].split('</div>', 1)[0]
        cards = CARD.findall(fragment)
        self.assertEqual(len(cards), len(records))
        self.assertGreaterEqual(len(cards), 200)
        for (category, name, description, url), item in zip(cards, records):
            with self.subTest(site=item["name"]):
                self.assertEqual(unescape(category), item["category"])
                self.assertEqual(unescape(name), item["name"])
                self.assertEqual(unescape(description), item["description"])
                self.assertEqual(unescape(url), item["url"])

    def test_js_does_not_embed_second_copy_of_catalog(self):
        js = (ROOT / "dist/assets/directory.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"const\\s+sites\\s*=\\s*\\[")
        self.assertIn("querySelectorAll('article.v6-card')", js)
        self.assertLess(len(js.encode("utf-8")), 10000)


if __name__ == "__main__":
    unittest.main()
