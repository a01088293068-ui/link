import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("linkwiki_build", ROOT / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class CanonicalURLTests(unittest.TestCase):
    def test_public_url(self):
        self.assertEqual(builder.public_url("https://linkwiki.info/categories/ai.html"),
                         "https://linkwiki.info/categories/ai")
        self.assertEqual(builder.public_url("https://linkwiki.info/index.html"),
                         "https://linkwiki.info/")
        self.assertEqual(builder.public_url("/guides/security.html#details"),
                         "/guides/security#details")
        self.assertEqual(builder.public_url("https://external.example/about.html"),
                         "https://external.example/about.html")

    def test_existing_relative_links(self):
        markup = ('<a href="../index.html">Home</a>'
                  '<a href="../guides/security.html#steps">Guide</a>'
                  '<a href="https://external.example/a.html">External</a>'
                  '<link href="https://linkwiki.info/categories/ai.html" rel="canonical">')
        output = builder.normalize_page_links(markup)
        self.assertIn('href="../"', output)
        self.assertIn('href="../guides/security#steps"', output)
        self.assertIn('href="https://external.example/a.html"', output)
        self.assertIn('href="https://linkwiki.info/categories/ai"', output)

    def test_generated_site_uses_extensionless_canonicals(self):
        dist = ROOT / "dist"
        if not (dist / "sitemap.xml").exists():
            self.skipTest("Run build.py before release verification")
        sitemap = ET.parse(dist / "sitemap.xml")
        urls = [node.text for node in sitemap.getroot().iter() if node.tag.endswith("}loc")]
        self.assertIn("https://linkwiki.info/categories/ai", urls)
        self.assertNotIn("https://linkwiki.info/categories/ai.html", urls)
        html = (dist / "categories" / "ai.html").read_text(encoding="utf-8")
        self.assertIn('href="https://linkwiki.info/categories/ai" rel="canonical"', html)


if __name__ == "__main__":
    unittest.main()
