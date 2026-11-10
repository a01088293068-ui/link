"""Protect new task-specific Korean guides and their crawlable category routes."""
from pathlib import Path
import unittest
from build import markdown, slug_for, extract_title, stable_post_lastmod, CATEGORY_LANDING
from seo.auto_seo import related_categories

ROOT = Path(__file__).resolve().parents[1]
GUIDES = {
    "seo-20261110-korean-sports-live-scores-guide": "/categories/sports",
    "seo-20261110-korean-ott-video-site-selection-guide": "/categories/video",
    "seo-20261110-overseas-korean-community-guide": "/categories/korean",
}

class KoreanTopicRouteTests(unittest.TestCase):
    def test_new_articles_use_task_specific_category_links(self):
        valid = {"/categories/" + slug for _, slug, _, _ in CATEGORY_LANDING}
        for slug, category in GUIDES.items():
            source = ROOT / "content" / (slug + ".md")
            with self.subTest(slug=slug):
                body = source.read_text(encoding="utf-8")
                self.assertGreater(len(body), 1800)
                self.assertEqual(slug_for(source), slug)
                self.assertEqual(stable_post_lastmod(source), "2026-11-10")
                links = {url for _, url in related_categories(extract_title(body))}
                self.assertIn(category, links)
                self.assertTrue(links.issubset(valid))
                html = markdown(body)
                self.assertIn('<div class="blog-table-scroll"><table>', html)
                self.assertGreaterEqual(html.count("<td>"), 15)
                self.assertIn('href="/directory"', html)
                self.assertIn('href="/guides/address-check"', html)

    def test_built_html_canonical_sitemap_and_category_cards(self):
        dist = ROOT / "dist"
        sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
        for slug, category in GUIDES.items():
            with self.subTest(slug=slug):
                url = "https://linkwiki.info/blog/" + slug + "/"
                article = dist / "blog" / slug / "index.html"
                self.assertTrue(article.exists(), slug)
                html = article.read_text(encoding="utf-8")
                self.assertIn('href="' + url + '" rel="canonical"', html)
                self.assertIn('<div class="blog-table-scroll"><table>', html)
                self.assertIn('<loc>' + url + '</loc>', sitemap)
                category_html = (dist / "categories" / (category.split("/")[-1] + ".html")).read_text(encoding="utf-8")
                self.assertIn('href="/blog/' + slug + '/"', category_html)

if __name__ == "__main__":
    unittest.main()
