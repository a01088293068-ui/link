from pathlib import Path
import re
import unittest

from build import synchronize_shared_footer


ROOT = Path(__file__).resolve().parents[1]


class SharedFooterRegressionTests(unittest.TestCase):
    def test_every_static_html_page_uses_the_same_footer_actions(self):
        published_root = ROOT / "dist"
        if not published_root.exists():
            self.skipTest("Production build not generated")
        pages = [
            path for path in published_root.rglob("*.html")
            if path.name != "naver8cd598bf6fee0ad116a386a3d915bb9f.html"
        ]
        self.assertGreaterEqual(len(pages), 20)
        for path in pages:
            source = path.read_text(encoding="utf-8")
            match = re.search(r'<footer class="footer">[\s\S]*?</footer>', source)
            with self.subTest(page=str(path.relative_to(ROOT))):
                self.assertIsNotNone(match, "page must have the shared footer")
                footer = match.group(0)
                self.assertIn('class="footer-cta"', footer)
                self.assertNotIn("linkwiki01.com", footer)
                self.assertNotIn("링크위키 바로가기", footer)
                self.assertIn('class="footer-secondary-action"', footer)
                self.assertIn('href="/directory"', footer)
                self.assertIn('class="footer-nav"', footer)
                self.assertNotIn("링크위키 본 사이트 방문", footer)

    def test_shared_footer_has_responsive_styles_and_generated_article_cache_bust(self):
        css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
        builder = (ROOT / "build.py").read_text(encoding="utf-8")
        self.assertIn(".footer-cta{", css)
        self.assertIn("@media(max-width:680px)", css)
        self.assertIn(".footer-cta-actions>.footer-primary-action", css)
        self.assertIn(".main-site-inline a", css)
        self.assertIn(".guide-related-links a", css)
        self.assertIn("assets/style.css?v=footer-system-20261117-v2", builder)


    def test_build_helper_replaces_every_page_footer_with_shared_markup(self):
        source = (
            '<html><body><main>Page content</main>'
            '<footer class="footer"><p>Old footer</p></footer></body></html>'
        )
        shared = '<footer class="footer"><nav><a href="/guides/link-faq">FAQ</a></nav></footer>'
        result = synchronize_shared_footer(source, shared)
        self.assertIn('href="/guides/link-faq"', result)
        self.assertNotIn("Old footer", result)
        self.assertIn("<main>Page content</main>", result)

    def test_build_helper_rejects_missing_or_duplicate_footers(self):
        shared = '<footer class="footer"></footer>'
        with self.assertRaisesRegex(RuntimeError, "found 0"):
            synchronize_shared_footer("<html><body>No footer</body></html>", shared)
        duplicate = (
            '<html><body><footer class="footer"></footer>'
            '<footer class="footer"></footer></body></html>'
        )
        with self.assertRaisesRegex(RuntimeError, "found 2"):
            synchronize_shared_footer(duplicate, shared)

    def test_build_helper_skips_non_html_verification_content(self):
        source = "google-site-verification: token"
        self.assertEqual(
            synchronize_shared_footer(source, '<footer class="footer"></footer>'),
            source,
        )


if __name__ == "__main__":
    unittest.main()
