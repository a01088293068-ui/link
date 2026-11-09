from pathlib import Path
import unittest

import build
import json


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

    def test_home_primary_keyword_intent_is_visible_and_consistent(self):
        source = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
        for phrase in ("주소모음", "링크모음", "사이트모음"):
            self.assertIn(phrase, source.split("</title>", 1)[0])
        count = len(json.loads((Path(__file__).resolve().parents[1] / "assets/verified-directory.json").read_text(encoding="utf-8")))
        self.assertIn(f'<h1 class="home-keyword-heading">주소모음·링크모음·사이트모음, {count}개 사이트 검색</h1>', source)
        self.assertIn('href="https://linkwiki.info/" rel="canonical"', source)
        self.assertIn('name="description"', source)
        self.assertIn("사이트 이름이나 도메인을 입력해 주소를 찾거나", source)
        self.assertIn("주소 위키에서 찾는 사이트 주소는 어떻게 확인하나요?", source)
        self.assertIn('href="/guides/address-check">사이트 주소 확인 방법</a>', source)

    def test_old_homepage_counts_are_synced_to_directory_data(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "index.html").read_text(encoding="utf-8")
        actual = len(json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8")))
        # Exercise the previous real failure: stale metadata, H1 and CTA count.
        old = source.replace(f"{actual}개", "183개")
        result = build.polish_home_intent(old)
        self.assertNotIn("183개", result)
        self.assertIn(f"{actual}개 사이트 검색", result)
        self.assertIn(f"등록 사이트 {actual}개", result)
        self.assertEqual(result.count('class="lw-search-quicklinks"'), 1)

    def test_home_structure_mismatch_is_explicit(self):
        with self.assertRaisesRegex(RuntimeError, "Homepage structure changed"):
            build.polish_home_intent("invalid template")

    def test_published_article_bottom_has_home_link(self):
        blog = Path(__file__).resolve().parents[1] / "dist" / "blog"
        for article in blog.glob("*/index.html"):
            content = article.read_text(encoding="utf-8")
            self.assertIn('href="/">주소모음·링크모음 홈</a>', content)
            self.assertIn('href="https://linkwiki01.com/" rel="noopener noreferrer">링크위키 바로가기</a>', content)


if __name__ == "__main__":
    unittest.main()
