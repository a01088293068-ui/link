import json
from pathlib import Path
import re
import unittest

import build


ROOT = Path(__file__).resolve().parents[1]


class CategoryCollectionSchemaTests(unittest.TestCase):
    def test_category_collection_schema_matches_real_published_records(self):
        records = [
            {"name": "큐넷", "url": "https://www.q-net.or.kr/", "category": "교육·취업"},
            {"name": "잡코리아", "url": "https://www.jobkorea.co.kr/", "category": "교육·취업"},
            {"name": "네이버", "url": "https://www.naver.com/", "category": "검색·포털"},
        ]
        script = build.category_collection_schema(
            records, "교육·취업", "education", "교육·취업"
        )
        match = re.fullmatch(
            r'<script type="application/ld\+json">(.*?)</script>', script, re.S
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(data["@type"], "CollectionPage")
        self.assertEqual(data["url"], "https://linkwiki.info/categories/education")
        self.assertEqual(data["mainEntity"]["@type"], "ItemList")
        self.assertEqual(data["mainEntity"]["numberOfItems"], 2)
        self.assertEqual(
            [item["name"] for item in data["mainEntity"]["itemListElement"]],
            ["큐넷", "잡코리아"],
        )
        self.assertEqual(
            [item["position"] for item in data["mainEntity"]["itemListElement"]],
            [1, 2],
        )

    def test_empty_category_does_not_publish_empty_collection(self):
        with self.assertRaisesRegex(RuntimeError, "empty category collection"):
            build.category_collection_schema([], "없는 분야", "missing", "없는 분야")

    def test_built_category_pages_include_visible_item_list_schema(self):
        dist = ROOT / "dist" / "categories" / "education.html"
        if not dist.exists():
            self.skipTest("Release build has not been generated")
        html = dist.read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(data["@type"], "CollectionPage")
        self.assertEqual(data["url"], "https://linkwiki.info/categories/education")
        items = data["mainEntity"]["itemListElement"]
        self.assertEqual(data["mainEntity"]["numberOfItems"], 27)
        self.assertEqual(len(items), 27)
        self.assertTrue(all(item.get("name") and item.get("url") for item in items))


if __name__ == "__main__":
    unittest.main()
