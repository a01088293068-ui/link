"""Category examples lead to real searchable sites without invented claims."""
import json
import unittest
from pathlib import Path
from urllib.parse import quote

from build import CATEGORY_LANDING, category_decision_guide

ROOT=Path(__file__).resolve().parents[1]

class CategorySearchEntryPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=json.loads((ROOT/"assets"/"verified-directory.json").read_text(encoding="utf-8"))

    def test_all_categories_link_to_actual_registered_names(self):
        for category, slug, _, _ in CATEGORY_LANDING:
            with self.subTest(slug=slug):
                html=category_decision_guide(slug,self.records)
                names=[record["name"] for record in self.records if record["category"]==category]
                self.assertGreaterEqual(len(names),2)
                for name in names[:2]:
                    self.assertIn('href="/directory?q='+quote(name,safe="")+'"',html)
                self.assertIn('href="/directory"',html)
                self.assertEqual(html.count('href="/directory?q='),2)

    def test_missing_category_examples_fails(self):
        with self.assertRaisesRegex(RuntimeError,"Insufficient sourced category examples"):
            category_decision_guide("community",[])

if __name__=="__main__":
    unittest.main()
