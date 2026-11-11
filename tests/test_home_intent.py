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

    def test_homepage_task_links_match_generic_directory_search_intent(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        html = build.homepage_task_paths(records)
        self.assertIn('href="/categories/"', html)
        self.assertIn('href="/guides/address-check"', html)
        self.assertIn('href="/directory?q=', html)
        self.assertIn("커뮤니티·웹툰·AI 도구·스포츠", html)
        self.assertIn("네이버 웹툰", html)
        self.assertNotIn("정부 민원, 연금·건강보험", html)
        self.assertEqual(html.count('class="blog-card"'), 3)
        without_sample = [r for r in records if r["name"] != "네이버 웹툰"]
        with self.assertRaisesRegex(RuntimeError, "not backed"):
            build.homepage_task_paths(without_sample)

    def test_directory_above_fold_category_comparison_uses_real_catalog(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        output = build.directory_quick_comparison(records, build.CATEGORY_LANDING)
        self.assertEqual(output.count("<li>"), len(build.CATEGORY_LANDING))
        self.assertIn('id="directory-quick-compare"', output)
        for category, slug, _, _ in build.CATEGORY_LANDING:
            count = sum(item.get("category") == category for item in records)
            self.assertIn(f'href="/categories/{slug}"', output)
            self.assertIn(f"{category} {count}개", output)
            self.assertIn(next(item["name"] for item in records if item.get("category") == category), output)
        self.assertNotIn("인기 순위", output.split("</p>", 1)[0])

    def test_directory_comparison_fails_if_category_has_no_listings(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        without_ai = [item for item in records if item.get("category") != "AI 도구"]
        with self.assertRaisesRegex(RuntimeError, "Missing active category"):
            build.directory_quick_comparison(without_ai, build.CATEGORY_LANDING)

    def test_generated_homepage_exposes_broad_directory_intent_without_redirects(self):
        path = Path(__file__).resolve().parents[1] / "dist" / "index.html"
        if not path.exists():
            self.skipTest("Generated release not built")
        html = path.read_text(encoding="utf-8")
        self.assertIn('class="wrap blog-home seo-home-task-paths"', html.split("</main>", 1)[0])
        self.assertIn("커뮤니티·웹툰·AI 도구·스포츠", html)
        self.assertIn('href="/categories/"', html)
        self.assertIn('href="/directory?q=', html)
        self.assertIn('action="/directory"', html)
        self.assertNotIn('href="/directory.html"', html)
        self.assertIn('href="https://linkwiki.info/" rel="canonical"', html)

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
