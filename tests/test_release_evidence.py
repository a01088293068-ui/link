"""Regression coverage for deterministic LinkWiki release build evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from seo.release_evidence import CATEGORY_PATHS, release_evidence


class ReleaseEvidenceTests(unittest.TestCase):
    def test_real_built_release_is_internally_consistent(self):
        dist = Path(__file__).resolve().parents[1] / "dist"
        if not dist.is_dir():
            self.skipTest("run python3 build.py first")
        manifest = release_evidence(dist)
        self.assertEqual(manifest["sites"], manifest["directory_cards"])
        self.assertEqual(manifest["sites"], manifest["js_records"])
        self.assertEqual(manifest["sites"], sum(manifest["categories"].values()))
        self.assertEqual(len(manifest["categories"]), len(CATEGORY_PATHS))
        self.assertFalse(manifest["public_deployment_verified"])
        self.assertFalse(manifest["google_indexing_verified"])
        self.assertFalse(manifest["rank_improvement_verified"])

    def test_rejects_stale_client_js_and_missing_category_card(self):
        with TemporaryDirectory() as temporary:
            dist = Path(temporary)
            (dist / "assets").mkdir()
            (dist / "categories").mkdir()
            records = [
                {"name": "예시 포털", "category": "검색·포털",
                 "url": "https://example.org/portal", "description": "테스트 설명"},
                {"name": "예시 AI", "category": "AI 도구",
                 "url": "https://example.org/ai", "description": "테스트 설명"},
            ]
            (dist / "assets/verified-directory.json").write_text(
                json.dumps(records, ensure_ascii=False), encoding="utf-8")
            js = dist / "assets/directory.js"
            original = "const sites=" + json.dumps(records, ensure_ascii=False) + ";(()=>"
            js.write_text(original, encoding="utf-8")
            (dist / "directory.html").write_text(
                '<article class="v6-card"></article>' * 2, encoding="utf-8")
            (dist / "index.html").write_text(
                "<h1>2개 사이트</h1>", encoding="utf-8")
            for category, slug in CATEGORY_PATHS.items():
                count = 1 if category in ("검색·포털", "AI 도구") else 0
                (dist / "categories" / (slug + ".html")).write_text(
                    '<article class="item"></article>' * count,
                    encoding="utf-8")
            self.assertEqual(release_evidence(dist)["sites"], 2)
            js.write_text("const sites=" + json.dumps(records[:-1], ensure_ascii=False)
                          + ";(()=>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JavaScript"):
                release_evidence(dist)
            js.write_text(original, encoding="utf-8")
            (dist / "categories/search.html").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "search"):
                release_evidence(dist)


if __name__ == "__main__":
    unittest.main()
