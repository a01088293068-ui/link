"""Regression coverage for five canonical Korean SEO guides in live release QA."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from email.message import Message
import unittest

from seo.live_release_check import (
    PRIORITY_GUIDE_SLUGS, SITE, article_body, check_page, check_sitemap,
    fetch_public, priority_guide_pages,
)


class PriorityGuideReleaseTests(unittest.TestCase):
    def test_exact_five_distinct_published_priority_guides(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(len(PRIORITY_GUIDE_SLUGS), 5)
        self.assertEqual(len(set(PRIORITY_GUIDE_SLUGS)), 5)
        for slug in PRIORITY_GUIDE_SLUGS:
            with self.subTest(slug=slug):
                self.assertTrue((root / "content" / (slug + ".md")).is_file())
        release = root / "dist"
        if (release / "blog").is_dir():
            self.assertEqual(len(priority_guide_pages(release)), 5)

    def test_stale_article_copy_detected_even_if_title_and_canonical_unchanged(self):
        path = "/blog/seo-20261111-mobile-address-directory-check/"
        body = ('<div class="blog-content"><p>모바일에서 주소를 확인합니다.</p></div>'
                '<a href="/directory">전체 목록</a>'
                '<a href="/categories/">카테고리</a>')
        expected = (f'<html><head><title>모바일 주소모음</title>'
                    f'<link rel="canonical" href="{SITE + path}"></head>'
                    f'<body><h1>모바일 주소모음</h1>{body}</body></html>')
        self.assertEqual(check_page(expected, expected, path), [])
        stale = expected.replace("모바일에서 주소를 확인합니다.", "이전 안내 문구")
        self.assertTrue(any("deployed guide body differs" in issue
                            for issue in check_page(expected, stale, path)))
        self.assertIsNone(article_body(expected.replace('class="blog-content"', 'class="other"')))
        self.assertTrue(any("guide body missing" in issue
                            for issue in check_page(expected, expected.replace(
                                'class="blog-content"', 'class="other"'), path)))

    def test_priority_articles_are_required_in_live_sitemap_only_for_real_build(self):
        locs = [SITE + "/", SITE + "/directory", SITE + "/categories/"]
        from seo.live_release_check import CATEGORY_PATHS
        locs += [SITE + path for path in CATEGORY_PATHS]
        base = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
            f"<url><loc>{item}</loc></url>" for item in locs) + "</urlset>"
        article = "/blog/" + PRIORITY_GUIDE_SLUGS[0] + "/"
        self.assertEqual(check_sitemap(base), [])
        self.assertIn("sitemap missing " + SITE + article,
                      check_sitemap(base, [article]))
        full = base.replace("</urlset>", f"<url><loc>{SITE + article}</loc></url></urlset>")
        self.assertEqual(check_sitemap(full, [article]), [])

    def test_priority_article_redirect_and_x_robots_header_are_rejected(self):
        class Response:
            status = 200
            def __init__(self, final, tag=""):
                self.final, self.headers = final, Message()
                if tag:
                    self.headers.add_header("X-Robots-Tag", tag)
            def geturl(self):
                return self.final
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b"<html>ok</html>"
        path = "/blog/" + PRIORITY_GUIDE_SLUGS[0] + "/"
        with patch("seo.live_release_check.urlopen", return_value=Response(SITE + path + "index.html")):
            with self.assertRaisesRegex(RuntimeError, "Canonical URL redirected"):
                fetch_public(path)
        with patch("seo.live_release_check.urlopen", return_value=Response(SITE + path, "googlebot: noindex")):
            with self.assertRaisesRegex(RuntimeError, "X-Robots-Tag"):
                fetch_public(path)
        with patch("seo.live_release_check.urlopen", return_value=Response(SITE + path)):
            self.assertIn("<html>ok</html>", fetch_public(path))


if __name__ == "__main__":
    unittest.main()
