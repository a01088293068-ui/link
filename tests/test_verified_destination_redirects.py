"""Prevent regression to superseded third-party redirect URLs."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DESTINATIONS = {
    "Microsoft Copilot": ("https://copilot.com/", "AI 도구"),
    "Gemini Notebook (구 NotebookLM)": ("https://notebook.google.com/", "AI 도구"),
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
        self.assertGreaterEqual(len(self.records), 200)
        self.assertEqual(len({item["url"] for item in self.records}), len(self.records))
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


    def test_redirected_korean_services_render_from_current_catalog_destinations(self):
        import build
        evidence = build.load_directory_evidence(self.records)
        cards = build.render_directory_catalog_cards(self.records, evidence)
        expected = {
            "티맵": ("https://www.tmapmobility.com/", "생활·교통·여행"),
            "네이버 밴드": ("https://www.band.us/about/intro", "커뮤니티"),
        }
        for name, (url, category) in expected.items():
            with self.subTest(name=name):
                self.assertEqual(self.by_name[name]["url"], url)
                self.assertEqual(self.by_name[name]["category"], category)
                self.assertIn('href="' + url + '"', cards)
                self.assertIn(url, evidence)
                self.assertEqual(evidence[url]["name"], name)
                self.assertEqual(evidence[url]["checked_on"], "2026-11-18")
        for category, path in (
            ("커뮤니티", ROOT / "categories" / "community.html"),
            ("생활·교통·여행", ROOT / "categories" / "travel.html"),
        ):
            rendered = build.sync_category_card_copy(path.read_text(encoding="utf-8"), self.records, category)
            url = expected["네이버 밴드"][0] if category == "커뮤니티" else expected["티맵"][0]
            self.assertIn('href="' + url + '"', rendered)

    def test_directory_javascript_uses_single_dom_backed_catalog(self):
        js = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        self.assertIn("querySelectorAll('article.v6-card')", js)
        self.assertNotIn("const sites=", js)
        self.assertIn("search.sortResults", js)


if __name__ == "__main__":
    unittest.main()
