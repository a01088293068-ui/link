from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MAIN_SERVICE = 'href="https://linkwiki01.com/"'


class SharedFooterRegressionTests(unittest.TestCase):
    def test_every_static_html_page_uses_the_same_footer_actions(self):
        pages = [
            path for path in ROOT.rglob("*.html")
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
                self.assertIn(EXPECTED_MAIN_SERVICE, footer)
                self.assertIn(">링크위키 바로가기 <span", footer)
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


if __name__ == "__main__":
    unittest.main()
