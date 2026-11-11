"""Verify distinct Korean search-intent guides survive the full Pages build."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
GUIDES = (
    "seo-20261111-address-directory-no-results",
    "seo-20261111-site-directory-selection-by-purpose",
    "seo-20261111-mobile-address-directory-check",
)


class KoreanKeywordClusterTests(unittest.TestCase):
    def test_articles_are_distinct_and_actionable(self):
        headings = []
        for slug in GUIDES:
            with self.subTest(slug=slug):
                content = (ROOT / "content" / (slug + ".md")).read_text(encoding="utf-8")
                self.assertGreaterEqual(len(content), 2000)
                title = content.splitlines()[0]
                self.assertTrue(title.startswith("# "))
                self.assertNotIn("**", content)
                self.assertIn("](/directory)", content)
                self.assertIn("](/categories/", content)
                self.assertGreaterEqual(content.count("## "), 5)
                headings.append(title)
        self.assertEqual(len(set(headings)), len(GUIDES))

    def test_articles_have_no_unresolved_internal_links(self):
        for slug in GUIDES:
            content = (ROOT / "content" / (slug + ".md")).read_text(encoding="utf-8")
            for target in re.findall(r"\]\((/[^)]+)\)", content):
                with self.subTest(article=slug, target=target):
                    clean = target.split("?", 1)[0].split("#", 1)[0]
                    if clean == "/":
                        file = ROOT / "index.html"
                    elif clean.startswith("/blog/"):
                        file = ROOT / "content" / (clean.strip("/").split("/")[-1] + ".md")
                    elif clean == "/categories/":
                        file = ROOT / "categories" / "index.html"
                        # Hub is generated at build time rather than sourced.
                        self.assertTrue((ROOT / "categories").is_dir())
                        continue
                    else:
                        file = ROOT / (clean.strip("/") + ".html")
                    self.assertTrue(file.is_file(), str(file))

    def test_published_pages_are_canonical_and_in_sitemap(self):
        dist = ROOT / "dist"
        if not (dist / "sitemap.xml").exists():
            self.skipTest("Build first: python3 build.py")
        root = ET.parse(dist / "sitemap.xml").getroot()
        indexed = {node.text for node in root.iter()
                   if node.tag.rsplit("}", 1)[-1] == "loc"}
        for slug in GUIDES:
            with self.subTest(slug=slug):
                url = "https://linkwiki.info/blog/" + slug + "/"
                self.assertIn(url, indexed)
                html = (dist / "blog" / slug / "index.html").read_text(encoding="utf-8")
                self.assertIn('href="' + url + '" rel="canonical"', html)
                self.assertIn('href="/directory"', html)
                self.assertIn('href="/categories/', html)
                self.assertNotIn('name="robots" content="noindex"', html)


if __name__ == "__main__":
    unittest.main()
