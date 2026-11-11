"""Tests for task-driven site discovery based on real LinkWiki catalog entries."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import unittest

from build import directory_everyday_task_paths
from seo.live_release_check import check_page, release_content_sections

ROOT = Path(__file__).resolve().parents[1]
PAIRS = (
    ("네이버 지도", "카카오맵"),
    ("ChatGPT", "DeepL"),
    ("Canva", "미리캔버스"),
    ("당근", "중고나라"),
    ("유튜브", "넷플릭스"),
    ("네이버 웹툰", "카카오웹툰"),
    ("빅카인즈", "국가통계포털 KOSIS"),
)


class EverydayTaskDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads(
            (ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8")
        )

    def test_seven_distinct_tasks_come_from_registered_services(self):
        html = directory_everyday_task_paths(self.records)
        names = {row["name"] for row in self.records}
        self.assertEqual(html.count("<li><strong>"), 7)
        self.assertEqual(html.count('class="lw-safety-note seo-everyday-tasks"'), 1)
        self.assertIn('id="directory-everyday-tasks"', html)
        self.assertNotIn("실시간 접속 확인 완료", html)
        self.assertNotIn("인기 순위 1위", html)
        for first, second in PAIRS:
            with self.subTest(first=first, second=second):
                self.assertIn(first, names)
                self.assertIn(second, names)
                self.assertIn(first, html)
                self.assertIn(second, html)
                from urllib.parse import quote
                self.assertIn('href="/directory?q=' + quote(first, safe="") + '"', html)
                self.assertIn('href="/directory?q=' + quote(second, safe="") + '"', html)
        self.assertEqual(html.count('href="/directory?q='), 14)

    def test_missing_registered_entry_fails_closed(self):
        without = [row for row in self.records if row["name"] != "미리캔버스"]
        with self.assertRaisesRegex(RuntimeError, "미리캔버스"):
            directory_everyday_task_paths(without)
        with self.assertRaises(RuntimeError):
            directory_everyday_task_paths([])

    def test_release_contains_real_comparison_and_jump_link(self):
        dist = ROOT / "dist" / "directory.html"
        if not dist.is_file():
            self.skipTest("Build first")
        page = dist.read_text(encoding="utf-8")
        section = directory_everyday_task_paths(self.records)
        self.assertIn(section, page)
        self.assertEqual(page.count('id="directory-everyday-tasks"'), 1)
        self.assertIn('href="#directory-everyday-tasks"', page)
        self.assertIn(section, release_content_sections(page, "/directory"))
        self.assertLess(page.index('id="site-purpose-comparison"'),
                        page.index('id="directory-everyday-tasks"'))

    def test_live_release_drift_detected_when_one_real_task_changes(self):
        base = '<html><head><title>Directory</title><link rel="canonical" href="https://linkwiki.info/directory"></head>'
        body = '<body><h1>주소모음·링크모음·사이트모음</h1>'
        html = base + body + directory_everyday_task_paths(self.records) + '</body></html>'
        older = html.replace("지도", "지도OLD", 1)
        self.assertNotEqual(release_content_sections(html, "/directory"),
                            release_content_sections(older, "/directory"))
        self.assertTrue(any("directory examples differ" in x
                            for x in check_page(html, older, "/directory")))


if __name__ == "__main__":
    unittest.main()
