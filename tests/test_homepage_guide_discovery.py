"""Require real direct homepage discovery paths for five Korean search-intent guides."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build import HOME_SEARCH_GUIDES, homepage_search_guide_links

ROOT = Path(__file__).resolve().parents[1]


class HomepageGuideDiscoveryTests(unittest.TestCase):
    def test_five_distinct_real_articles_are_linked_once(self):
        self.assertEqual(len(HOME_SEARCH_GUIDES), 5)
        self.assertEqual(len({slug for slug, _, _ in HOME_SEARCH_GUIDES}), 5)
        markup = homepage_search_guide_links()
        self.assertEqual(markup.count("<li>"), 5)
        self.assertIn('class="wrap seo-related-links seo-home-search-guides"', markup)
        for slug, label, _ in HOME_SEARCH_GUIDES:
            with self.subTest(slug=slug):
                self.assertTrue((ROOT / "content" / (slug + ".md")).is_file())
                self.assertEqual(markup.count('href="/blog/' + slug + '/"'), 1)
                self.assertIn(label, markup)
        self.assertNotIn('href="https://', markup)

    def test_missing_guide_refuses_to_publish_fake_link(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "Missing published homepage search guide"):
                homepage_search_guide_links(Path(directory))

    def test_generated_homepage_links_to_real_generated_articles(self):
        dist = ROOT / "dist"
        if not (dist / "index.html").exists():
            self.skipTest("Run python3 build.py first")
        html = (dist / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="wrap seo-related-links seo-home-search-guides"'), 1)
        start = html.index('class="wrap seo-related-links seo-home-search-guides"')
        section = html[start:html.index("</section>", start)]
        for slug, _, _ in HOME_SEARCH_GUIDES:
            with self.subTest(slug=slug):
                # Existing homepage sections may link to these articles too.
                self.assertEqual(section.count('href="/blog/' + slug + '/"'), 1)
                self.assertTrue((dist / "blog" / slug / "index.html").is_file())
        self.assertLess(html.index('seo-home-search-guides'), html.index('</main>'))


if __name__ == "__main__":
    unittest.main()
