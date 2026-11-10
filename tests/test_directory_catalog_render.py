"""Content changes must reach the crawlable HTML, not only JSON or JavaScript."""
import json
import re
import unittest
from html import unescape
from pathlib import Path

from build import render_directory_catalog_cards, replace_directory_catalog_cards

ROOT = Path(__file__).resolve().parents[1]


class CatalogRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(
            (ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))

    def test_all_211_records_render_as_safe_crawlable_html(self):
        html = render_directory_catalog_cards(self.records)
        self.assertEqual(html.count('<article class="v6-card">'), len(self.records))
        self.assertEqual(html.count('rel="noopener noreferrer external"'), len(self.records))
        self.assertEqual(html.count('target="_blank"'), len(self.records))
        self.assertIn("내보내기와 사용 범위 조건", html)

    def test_description_edit_changes_html_without_hand_editing_directory(self):
        source = ('<main><div class="v6-grid" id="v6-results">'
                  'obsolete cards</div></main>')
        original = replace_directory_catalog_cards(source, self.records)
        edited = [dict(item) for item in self.records]
        edited[0]["description"] = "서로 다른 방문 목적에 맞춰 선택하는 설명입니다."
        updated = replace_directory_catalog_cards(source, edited)
        self.assertNotEqual(original, updated)
        self.assertIn("서로 다른 방문 목적", updated)
        self.assertNotIn("obsolete cards", updated)

    def test_catalog_html_escapes_external_text_and_attribute_values(self):
        entries = [dict(self.records[i % len(self.records)]) for i in range(200)]
        for i, item in enumerate(entries):
            item["url"] = "https://example.net/p/" + str(i)
        entries[0]["name"] = '<script>alert("x")</script>'
        entries[0]["description"] = '비교 & 확인 <내용>'
        html = render_directory_catalog_cards(entries)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("비교 &amp; 확인 &lt;내용&gt;", html)

    def test_invalid_or_duplicate_catalog_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unexpectedly empty"):
            render_directory_catalog_cards([])
        items = [dict(self.records[i % len(self.records)]) for i in range(200)]
        items[-1] = dict(items[0])
        with self.assertRaisesRegex(RuntimeError, "Duplicate directory URL"):
            render_directory_catalog_cards(items)


if __name__ == "__main__":
    unittest.main()
