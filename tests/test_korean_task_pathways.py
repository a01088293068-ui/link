"""Regression coverage for task-driven links to real Korean service records."""
import json
import unittest
from pathlib import Path

from build import category_article_links, directory_task_paths
from seo.auto_seo import related_categories

ROOT = Path(__file__).resolve().parents[1]

class KoreanTaskPathwayTests(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))

    def test_seven_tasks_are_grounded_in_registered_names(self):
        fragment = directory_task_paths(self.records)
        self.assertEqual(fragment.count("<li><strong>"), 13)
        for name in ("국민신문고", "정부24", "KIPRIS 지식재산정보검색",
                     "특허로", "K-Startup 창업지원포털", "기업마당",
                     "국세청 홈택스", "위택스", "국민건강보험공단",
                     "국민연금공단", "고용24", "한국장학재단",
                     "기상청 날씨누리", "서울시 교통정보 TOPIS", "국민안전24"):
            with self.subTest(name=name):
                self.assertIn(name, [r["name"] for r in self.records])
                self.assertIn(name, fragment)
        self.assertNotIn('href="http://', fragment)

    def test_missing_registered_service_fails_loudly(self):
        filtered = [x for x in self.records if x["name"] != "위택스"]
        with self.assertRaisesRegex(RuntimeError, "위택스"):
            directory_task_paths(filtered)

    def test_category_references_more_real_articles_but_never_invents_urls(self):
        posts = [{"title": f"국내 민원 활용 안내 {i}", "url": f"/blog/guide-{i}/"}
                 for i in range(7)]
        selected = category_article_links(posts, "search")
        self.assertEqual([p["url"] for p in selected],
                         [f"/blog/guide-{i}/" for i in range(5)])
        self.assertTrue(all("/categories/search" in
                            [u for _, u in related_categories(p["title"])]
                            for p in selected))

if __name__ == "__main__":
    unittest.main()
