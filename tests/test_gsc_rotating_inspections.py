"""Ensure scheduled GSC inspections eventually cover older real guides."""
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "gsc_rotating_inspection_test", ROOT / "seo" / "search_console_monitor.py"
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class RotatingInspectionTests(unittest.TestCase):
    def make_corpus(self, root, n):
        posts = root / "content"
        posts.mkdir()
        for i in range(n):
            (posts / f"seo-20261111-example-{i:03}.md").write_text(
                "# 안내 " + str(i) + "\n" + "실제 사이트 목적 구별 방법을 설명합니다. " * 10,
                encoding="utf-8"
            )
        (posts / "not-published.txt").write_text("invalid")
        (posts / "seo-20261111-too-short.md").write_text("# short")
        return posts

    def test_three_per_day_eventually_cover_every_real_published_article(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_corpus(root, 17)
            observed = []
            first = date(2026, 11, 11)
            for day in range(6):
                batch = monitor.rotating_inspection_urls(first + timedelta(days=day),
                                                         limit=3, root=root)
                self.assertEqual(len(batch), 3)
                self.assertEqual(len(set(batch)), 3)
                observed.extend(batch)
            self.assertEqual(len(set(observed)), 17)
            self.assertTrue(all("too-short" not in url for url in observed))

    def test_date_string_is_reproducible_and_does_not_scan_fake_urls(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_corpus(root, 5)
            a = monitor.rotating_inspection_urls("2026-11-15", root=root)
            b = monitor.rotating_inspection_urls(date(2026, 11, 15), root=root)
            self.assertEqual(a, b)
            self.assertEqual(len(a), 3)
            self.assertTrue(all(url.startswith("https://linkwiki.info/blog/") for url in a))

    def test_priority_landing_and_exact_queries_precede_rotating_urls(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_corpus(root, 27)
            with patch.object(monitor, "ROOT", root):
                rows = [{
                    "keys": ["주소모음", "https://linkwiki.info/guides/address-check"],
                    "impressions": 10
                }]
                selected = monitor.inspection_targets(
                    [], limit=20, core_query_pages=rows, as_of=date(2026, 11, 11))
            self.assertEqual(selected[:3], list(monitor.INSPECT_URLS[:3]))
            self.assertIn("https://linkwiki.info/categories/community", selected)
            self.assertIn("https://linkwiki.info/guides/address-check", selected)
            rotating = monitor.rotating_inspection_urls(date(2026, 11, 11), limit=2, root=root)
            self.assertTrue(all(url in selected for url in rotating))
            self.assertLessEqual(len(selected), 20)

    def test_legacy_exact_search_landing_is_not_dropped(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_corpus(root, 25)
            with patch.object(monitor, "ROOT", root):
                selected = monitor.inspection_targets(
                    [], core_query_pages=[{
                        "keys": ["사이트모음", "https://linkwiki.info/guides/security.html"],
                        "impressions": 3
                    }], as_of=date(2026, 11, 12))
            self.assertIn("https://linkwiki.info/guides/security", selected)
            self.assertIn("https://linkwiki.info/guides/security.html", selected)
            self.assertLessEqual(len(selected), 20)

    def test_small_test_limit_keeps_historical_selection(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_corpus(root, 20)
            with patch.object(monitor, "ROOT", root):
                small = monitor.inspection_targets([], limit=5, as_of=date(2026, 11, 11))
            self.assertEqual(small, list(monitor.INSPECT_URLS[:5]))


if __name__ == "__main__":
    unittest.main()
