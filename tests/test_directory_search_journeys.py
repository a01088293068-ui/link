"""Regression checks for real search journeys in the canonical directory."""
from pathlib import Path
import unittest

import build

ROOT = Path(__file__).resolve().parents[1]
GUIDES = (
    ("검색 결과가 없으면 어떻게 다시 찾나요?", "seo-20261111-address-directory-no-results"),
    ("서비스를 실제 용도로 비교하려면?", "seo-20261111-site-directory-selection-by-purpose"),
    ("휴대전화에서는 주소를 어떻게 확인하나요?", "seo-20261111-mobile-address-directory-check"),
)


class DirectorySearchJourneysTests(unittest.TestCase):
    def test_each_journey_uses_real_published_article(self):
        posts = []
        for question, slug in GUIDES:
            body = (ROOT / "content" / (slug + ".md")).read_text(encoding="utf-8")
            posts.append({"title": body.splitlines()[0][2:], "url": "/blog/" + slug + "/"})
        # Old published search/browse/ad guide must also be represented to meet
        # the existing minimum of two distinct guide URLs.
        posts.extend([
            {"title": "주소모음 검색 실전 가이드", "url": "/blog/seo-20261111-address-directory-search-examples/"},
            {"title": "링크모음·사이트모음 비교 기준", "url": "/blog/seo-20261111-links-sites-comparison-checklist/"},
        ])
        fragment = build.directory_relevant_guides(posts)
        for question, slug in GUIDES:
            with self.subTest(question=question):
                self.assertIn(question, fragment)
                self.assertEqual(fragment.count('href="/blog/' + slug + '/"'), 1)
        self.assertEqual(fragment.count('<li>'), 5)
        self.assertNotIn('href="/blog/nonexistent', fragment)

    def test_generated_directory_contains_contextual_links(self):
        html_path = ROOT / "dist" / "directory.html"
        if not html_path.exists():
            self.skipTest("Release not built")
        html = html_path.read_text(encoding="utf-8")
        for _, slug in GUIDES:
            with self.subTest(slug=slug):
                self.assertIn('href="/blog/' + slug + '/"', html)
                self.assertTrue((ROOT / "dist" / "blog" / slug / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
