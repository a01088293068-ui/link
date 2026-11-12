"""Guarantee Korean category explainers use real registered destinations."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "seo-20261110-korean-community-directory-guide.md",
    "seo-20261110-korean-webtoon-platform-guide.md",
    "seo-20261110-korean-public-services-guide.md",
    "seo-20261110-korean-business-portals-guide.md",
    "seo-20261110-korean-education-sites-guide.md",
    "seo-20261110-korean-ai-tools-by-task-guide.md",
    "seo-20261110-korean-sports-live-scores-guide.md",
    "seo-20261110-korean-ott-video-site-selection-guide.md",
    "seo-20261110-overseas-korean-community-guide.md",
)
PUBLIC_SERVICE_COMPARISONS = (
    "/blog/seo-20261111-gov24-epeople-complaint-certificate/",
    "/blog/seo-20261111-tax-hometax-wetax-difference/",
    "/blog/seo-20261111-public-data-vs-kosis-usage/",
)
CATEGORIES = (
    "community", "korean", "comics-directory", "webtoon",
    "ai", "search", "sports", "video",
)

class KoreanTopicGuidesTests(unittest.TestCase):
    def test_real_official_destinations_and_internal_links(self):
        directory = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        registered_urls = {x["url"] for x in directory}
        for filename in SOURCES:
            with self.subTest(filename=filename):
                text = (ROOT / "content" / filename).read_text(encoding="utf-8")
                self.assertGreater(len(text), 1200)
                self.assertTrue(text.startswith("# "))
                external = re.findall(r"\]\((https://[^)]+)\)", text)
                self.assertGreaterEqual(len(external), 5)
                self.assertTrue(all(url in registered_urls for url in external),
                                "All cited services must be actual catalog URLs")
                internal = re.findall(r"\]\((/[^)]+)\)", text)
                self.assertGreaterEqual(len(internal), 2)
                expected = ("/directory", "/guides/address-check")
                if filename == "seo-20261110-korean-public-services-guide.md":
                    expected += PUBLIC_SERVICE_COMPARISONS
                    for url in PUBLIC_SERVICE_COMPARISONS:
                        self.assertIn(url, internal)
                        self.assertTrue((ROOT / "content" / (url.strip("/").split("/")[-1] + ".md")).is_file())
                for url in internal:
                    if url.startswith("/categories/"):
                        self.assertIn(url.split("/")[2], CATEGORIES)
                    else:
                        self.assertIn(url, expected)
    def test_distinct_task_subjects(self):
        titles = [(ROOT / "content" / f).read_text(encoding="utf-8").splitlines()[0]
                  for f in SOURCES]
        self.assertEqual(len(titles), len(set(titles)))
        self.assertIn("커뮤니티", titles[0])
        self.assertIn("웹툰", titles[1])

if __name__ == "__main__":
    unittest.main()
