import json
import unittest
from datetime import date
from pathlib import Path

import build


ROOT = Path(__file__).resolve().parents[1]


class DirectoryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.evidence = build.load_directory_evidence(cls.records)

    def test_source_records_match_published_sites_and_do_not_claim_unchecked_items(self):
        self.assertEqual(7, len(self.evidence))
        for url, row in self.evidence.items():
            self.assertEqual(url, row["url"])
            self.assertLessEqual(date.fromisoformat(row["checked_on"]), date.today())

    def test_source_and_check_date_are_visible_on_directory_cards(self):
        html = build.render_directory_catalog_cards(self.records, self.evidence)
        self.assertEqual(7, html.count('class="directory-evidence"'))
        self.assertIn("2026-11-14", html)
        self.assertIn("https://www.scourt.go.kr/work2025/helpinfo.html", html)
        self.assertIn("2025-01-31", html)

    def test_each_primary_search_intent_has_its_own_useful_task(self):
        html = build.directory_keyword_intents(self.records)
        self.assertIn('id="intent-address-collection"', html)
        self.assertIn('id="intent-link-collection"', html)
        self.assertIn('id="intent-site-collection"', html)
        self.assertIn("현재 작동 여부", html)


if __name__ == "__main__":
    unittest.main()
