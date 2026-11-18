"""Ensure new domestic community listings have current first-party source evidence."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KoreanCommunityCatalogTests(unittest.TestCase):
    def test_82cook_and_naver_band_are_live_catalog_entries_with_source_evidence(self):
        catalog = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "assets" / "directory-evidence.json").read_text(encoding="utf-8"))
        by_url = {row["url"]: row for row in catalog}
        evidence_by_url = {row["url"]: row for row in evidence}
        expected = {
            "https://www.82cook.com/": ("82쿡", "service_page"),
            "https://www.band.us/about/intro": ("네이버 밴드", "agency_guide"),
        }
        for url, (name, evidence_type) in expected.items():
            with self.subTest(url=url):
                self.assertIn(url, by_url)
                self.assertEqual(by_url[url]["name"], name)
                self.assertEqual(by_url[url]["category"], "커뮤니티")
                self.assertIn(url, evidence_by_url)
                self.assertEqual(evidence_by_url[url]["name"], name)
                self.assertEqual(evidence_by_url[url]["evidence_type"], evidence_type)
                self.assertEqual(evidence_by_url[url]["checked_on"], "2026-11-18")
                self.assertTrue(evidence_by_url[url]["source_url"].startswith("https://"))
                self.assertGreater(len(evidence_by_url[url]["scope"]), 20)

    def test_catalog_and_evidence_counts_stay_synchronized(self):
        catalog = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "assets" / "directory-evidence.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(catalog), 361)
        self.assertGreaterEqual(len(evidence), 292)
        self.assertLess(len(evidence), len(catalog))


if __name__ == "__main__":
    unittest.main()
