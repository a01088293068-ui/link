"""Prevent regression to superseded third-party redirect URLs."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS = {
    "Microsoft Copilot": ("https://copilot.com/", "AI 도구"),
    "NotebookLM": ("https://notebook.google.com/", "AI 도구"),
    "Runway": ("https://runway.com/", "AI 도구"),
    "Plex": ("https://watch.plex.tv/", "영상·OTT"),
}
LEGACY_URLS = (
    "https://copilot.microsoft.com/",
    "https://notebooklm.google.com/",
    "https://runwayml.com/",
    "https://www.plex.tv/",
)

class UpdatedDestinationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.by_name = {row["name"]: row for row in cls.records}

    def test_verified_catalog_matches_correct_service_domains(self):
        self.assertEqual(len(self.records), 211)
        self.assertEqual(len({item["url"] for item in self.records}), 211)
        for name, (url, category) in DESTINATIONS.items():
            with self.subTest(name=name):
                row = self.by_name[name]
                self.assertEqual(row["url"], url)
                self.assertEqual(row["category"], category)
                self.assertEqual(urlsplit(url).scheme, "https")
        self.assertFalse(any(item["url"] in LEGACY_URLS for item in self.records))

    def test_all_static_user_visible_sites_link_directly_to_updated_urls(self):
        for page in ("directory.html", "categories/ai.html", "categories/video.html"):
            source = (ROOT / page).read_text(encoding="utf-8")
            for name, (url, category) in DESTINATIONS.items():
                if page == "categories/ai.html" and category != "AI 도구":
                    continue
                if page == "categories/video.html" and category != "영상·OTT":
                    continue
                with self.subTest(page=page, name=name):
                    self.assertIn('href="' + url + '"', source)
                    self.assertIn(urlsplit(url).hostname + "</span>", source)
            for old in LEGACY_URLS:
                self.assertNotIn('href="' + old + '"', source)

    def test_directory_javascript_preserves_exact_published_catalog(self):
        js = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("const sites="))
        marker = js.index("];(()=>")
        self.assertEqual(json.loads(js[len("const sites="):marker+1]), self.records)

if __name__ == "__main__":
    unittest.main()
