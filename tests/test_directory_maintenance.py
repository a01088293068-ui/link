"""Public directory maintenance data stays sourced and refuses false uptime claims."""
from pathlib import Path
import json
import unittest

from build import CATEGORY_LANDING
from seo.directory_maintenance import render
from seo.directory_release_gate import validate_maintenance_page

ROOT = Path(__file__).resolve().parents[1]

class DirectoryMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.changes = json.loads((ROOT / "seo/significant-page-updates.json").read_text(encoding="utf-8"))

    def test_actual_categorized_counts_and_disclosures(self):
        output = render(self.records, self.changes, CATEGORY_LANDING)
        self.assertIn(str(len(self.records)) + "개 사이트", output)
        for category, slug, title, _ in CATEGORY_LANDING:
            with self.subTest(slug=slug):
                self.assertIn('href="/categories/' + slug + '"', output)
                count = sum(r["category"] == category for r in self.records)
                self.assertIn(str(count) + "개", output)
        self.assertEqual(output.count("<tr><th><a href=\"/categories/"), len(CATEGORY_LANDING))
        self.assertIn("접속 확인일이 아닙니다", output)
        self.assertIn("실시간 정상 운영", output)
        self.assertIn('href="/guides/address-check"', output)

    def test_release_gate_rejects_stale_total_and_category_counts(self):
        output = render(self.records, self.changes, CATEGORY_LANDING)
        self.assertEqual(validate_maintenance_page(output, self.records), [])
        stale_total = output.replace(
            f"현재 {len(self.records)}개 사이트가 등록되어 있습니다.",
            "현재 337개 사이트가 등록되어 있습니다.",
        )
        self.assertIn(
            "maintenance page total does not match verified directory data",
            validate_maintenance_page(stale_total, self.records),
        )
        stale_category = output.replace("<td>33개</td>", "<td>32개</td>", 1)
        self.assertTrue(any(
            issue.startswith("maintenance page category count mismatch:")
            for issue in validate_maintenance_page(stale_category, self.records)
        ))

    def test_fabricated_or_missing_edit_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            render(self.records, {}, CATEGORY_LANDING)
        with self.assertRaises(ValueError):
            render(self.records, {"/directory": "2026-13-99"}, CATEGORY_LANDING)

    def test_missing_category_cannot_be_published(self):
        remaining = [x for x in self.records if x["category"] != "AI 도구"]
        with self.assertRaisesRegex(ValueError, "Missing category"):
            render(remaining, self.changes, CATEGORY_LANDING)

    def test_generated_release_is_linked_and_sitemapped(self):
        directory = (ROOT / "dist/directory.html").read_text(encoding="utf-8")
        guide = ROOT / "dist/guides/directory-maintenance.html"
        sitemap = (ROOT / "dist/sitemap.xml").read_text(encoding="utf-8")
        self.assertIn('href="/guides/directory-maintenance"', directory)
        self.assertTrue(guide.is_file())
        built = guide.read_text(encoding="utf-8")
        self.assertIn(str(len(self.records)) + "개 사이트", built)
        self.assertIn('href="https://linkwiki.info/guides/directory-maintenance"', built)
        self.assertIn("<loc>https://linkwiki.info/guides/directory-maintenance</loc>", sitemap)

if __name__ == "__main__":
    unittest.main()
