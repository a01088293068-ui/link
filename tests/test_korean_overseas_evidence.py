"""Regression tests for freshly checked Korean-language overseas directory evidence."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KoreanOverseasEvidenceTests(unittest.TestCase):
    def test_newly_checked_korean_language_services_have_first_party_page_evidence(self):
        records = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "assets" / "directory-evidence.json").read_text(encoding="utf-8"))
        catalog = {row["url"]: row for row in records}
        checked = {row["url"]: row for row in evidence}
        expected = {
            "https://www.newyorkkorea.net/main/index.html",
            "https://thaiholic.com/",
            "https://www.vinahanin.com/",
            "https://www.canadapia.com/",
            "https://www.hanasia.com/",
            "https://www.haninsinmun.com/",
            "https://www.kyomin.org/?ckattempt=1",
            "https://www.chinatalk.net/",
            "https://www.dalsaram.com/main_VER2.php",
            "https://www.workingus.com/",
            "https://www.kosarang.net/g4/index.php",
            "https://www.hungaryej.com/",
            "https://www.francezone.com/",
            "https://channel.cafe/tabs/home",
            "https://www.korean.net/web/main/main",
            "https://www.topdigital.com.au/",
            "https://housamo.com/",
        }
        self.assertTrue(expected.issubset(checked))
        for url in expected:
            with self.subTest(url=url):
                self.assertIn(url, catalog)
                row = checked[url]
                self.assertEqual(row["source_url"], url)
                self.assertEqual(row["evidence_type"], "service_page")
                self.assertEqual(row["checked_on"], "2026-11-18")
                self.assertGreater(len(row["scope"]), 25)

    def test_evidence_count_is_not_misrepresented_as_full_catalog_verification(self):
        records = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "assets" / "directory-evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(len(records), 360)
        self.assertEqual(len(evidence), 291)
        self.assertLess(len(evidence), len(records))


if __name__ == "__main__":
    unittest.main()
