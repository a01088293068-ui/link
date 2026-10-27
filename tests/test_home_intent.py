from pathlib import Path
import unittest

import build


class HomeIntentTests(unittest.TestCase):
    def test_home_preserves_existing_cta_and_adds_navigation(self):
        source = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        modified = build.polish_home_intent(source)
        self.assertIn("링크위키 바로가기", modified)
        self.assertIn("https://linkwiki01.com/", modified)
        self.assertIn('href="/categories/"', modified)
        self.assertIn('href="/directory.html"', modified)
        self.assertIn("실시간 접속 확인을 보증하지 않습니다", modified)
        self.assertEqual(modified.count('class="lw-search-quicklinks"'), 1)

    def test_home_structure_mismatch_is_explicit(self):
        with self.assertRaisesRegex(RuntimeError, "Homepage structure changed"):
            build.polish_home_intent("invalid template")

    def test_published_article_bottom_has_home_link(self):
        article = (Path(__file__).resolve().parents[1] / "dist" / "blog" /
                   "address-directory-safety-guide" / "index.html")
        if article.exists():
            self.assertIn('href="/">주소모음·링크모음 홈</a>', article.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
