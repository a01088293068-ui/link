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
        dist = ROOT / "dist" / "categories"
        if not dist.exists():
            self.skipTest("Release build has not been generated")
        records = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        for category, slug, heading, _purpose in build.CATEGORY_LANDING:
            with self.subTest(category=category, slug=slug):
                html = (dist / f"{slug}.html").read_text(encoding="utf-8")
                match = re.search(
                    r'<script type="application/ld\+json">(.*?)</script>', html, re.S
                )
                self.assertIsNotNone(match)
                data = json.loads(match.group(1))
                self.assertEqual(data["@type"], "CollectionPage")
                self.assertEqual(data["url"], f"https://linkwiki.info/categories/{slug}")
                self.assertEqual(data["name"], f"{heading} 사이트모음")
                self.assertEqual(data["mainEntity"]["name"], f"{heading} 등록 사이트")
                items = data["mainEntity"]["itemListElement"]
                expected_records = [record for record in records if record.get("category") == category]
                self.assertEqual(data["mainEntity"]["numberOfItems"], len(expected_records))
                self.assertEqual(len(items), len(expected_records))
                self.assertEqual(
                    [item["name"] for item in items],
                    [record["name"] for record in expected_records],
                )



if __name__ == "__main__":
    unittest.main()
