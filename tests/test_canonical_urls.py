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

    def test_category_hub_links_to_full_directory_with_dynamic_site_count(self):
        dist = ROOT / "dist"
        if not (dist / "categories" / "index.html").exists():
            self.skipTest("Run build.py before release verification")
        hub = (dist / "categories" / "index.html").read_text(encoding="utf-8")
        count = len(__import__("json").loads(
            (ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8")))
        self.assertIn(
            f'href="/directory">{count}개 사이트 이름·도메인 전체 검색</a>',
            hub,
        )

    def test_category_hub_and_existing_pages_link_each_other(self):
        dist = ROOT / "dist"
        if not (dist / "categories" / "index.html").exists():
            self.skipTest("Run build.py before release verification")
        hub = (dist / "categories" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count('개 등록 사이트'), len(builder.CATEGORY_LANDING))
        self.assertIn('href="https://linkwiki.info/categories/"', hub)
        for _, slug, _, _ in builder.CATEGORY_LANDING:
            self.assertIn(f'href="/categories/{slug}"', hub)
            page = (dist / "categories" / f"{slug}.html").read_text(encoding="utf-8")
            self.assertIn('href="/categories/"', page)
        self.assertIn('href="/categories/"', (dist / "index.html").read_text(encoding="utf-8"))


    def test_source_sitemaps_contain_only_canonical_public_urls(self):
        for name in ("sitemap.xml", "sitemap-v2.xml"):
            sitemap = ET.parse(ROOT / name)
            urls = [node.text for node in sitemap.getroot().iter()
                    if node.tag.endswith("}loc")]
            self.assertTrue(urls, f"{name} must contain URLs")
            self.assertEqual(len(urls), len(set(urls)), f"{name} has duplicate URLs")
            for url in urls:
                self.assertTrue(url.startswith("https://linkwiki.info/"), url)
                self.assertFalse(url.endswith(".html"), url)
                self.assertNotIn("http://linkwiki.info/", url, url)

if __name__ == "__main__":
    unittest.main()
