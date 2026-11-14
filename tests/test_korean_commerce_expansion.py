"""Guard Korean commerce category growth and first-party evidence."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "오늘의집": ("https://ohou.se/", "https://ohou.se/"),
    "당근": ("https://www.daangn.com/kr/", "https://www.daangn.com/kr/"),
    "에이블리": ("https://mobile.a-bly.com/", "https://mobile.a-bly.com/"),
    "W컨셉": ("https://www.wconcept.co.kr/", "https://display.wconcept.co.kr/rn/women"),
}


class KoreanCommerceExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.evidence = json.loads((ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))

    def test_four_korean_commerce_destinations_are_classified_and_unique(self):
        by_name = {row["name"]: row for row in self.records}
        self.assertEqual(len(self.records), 337)
        self.assertEqual(len(by_name), len(self.records))
        self.assertEqual(sum(row["category"] == "쇼핑·가격비교" for row in self.records), 16)
        for name, (url, _) in EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["url"], url)
                self.assertEqual(by_name[name]["category"], "쇼핑·가격비교")
                self.assertGreaterEqual(len(by_name[name]["description"]), 65)
                self.assertTrue(by_name[name]["description"].endswith("세요."))

    def test_each_addition_has_first_party_service_page_evidence(self):
        by_url = {row["url"]: row for row in self.evidence}
        for name, (url, source) in EXPECTED.items():
            with self.subTest(name=name):
                row = by_url[url]
                self.assertEqual(row["name"], name)
                self.assertEqual(row["source_url"], source)
                self.assertEqual(row["evidence_type"], "service_page")
                self.assertEqual(row["checked_on"], "2026-11-14")
                self.assertEqual(row["freshness_days"], 180)

    def test_shopping_entries_remain_in_canonical_category_order(self):
        shopping = [row for row in self.records if row["category"] == "쇼핑·가격비교"]
        self.assertEqual([row["name"] for row in shopping[-4:]],
                         ["에이블리", "W컨셉", "오늘의집", "당근"])
        self.assertEqual(len({row["url"] for row in self.records}), len(self.records))


if __name__ == "__main__":
    unittest.main()
