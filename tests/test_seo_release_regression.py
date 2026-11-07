from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from build import add_breadcrumb_data, normalize_page_links, stable_post_lastmod, category_article_links
import json
import re
from seo import auto_seo


class SEOReleaseRegressionTests(unittest.TestCase):
    def test_latest_published_article_is_in_built_sitemap_with_matching_canonical(self):
        root = Path(__file__).resolve().parents[1]
        posts = sorted((root / "content").glob("seo-*.md"))
        self.assertTrue(posts, "No published SEO article available for smoke test")
        slug = posts[-1].stem
        public_path = f"/blog/{slug}/"
        url = "https://linkwiki.info" + public_path
        output = root / "dist"
        sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"<loc>{url}</loc>", sitemap)
        html_path = output / "blog" / slug / "index.html"
        self.assertTrue(html_path.is_file(), f"Missing published article: {html_path}")
        html = html_path.read_text(encoding="utf-8")
        self.assertIn(f'href="{url}"', html)
        self.assertIn('name="robots" content="index,follow"', html)
        self.assertNotIn('name="robots" content="noindex', html)

    def test_category_article_links_only_relevant_published_guides(self):
        posts = [
            {"title": "검색 포털 링크모음 목적별 비교", "url": "/blog/search-example/"},
            {"title": "사이트모음 비교 기준", "url": "/blog/general-example/"},
            {"title": "스포츠 경기 일정 사이트 비교", "url": "/blog/sports-example/"},
        ]
        self.assertEqual(category_article_links(posts, "search"),
                         [posts[0]])
        self.assertEqual(category_article_links(posts, "sports"),
                         [posts[2]])
        self.assertEqual(category_article_links(posts, "ai"), [])

    def test_category_page_links_to_actual_search_post_after_build(self):
        root = Path(__file__).resolve().parents[1]
        output = root / "dist" / "categories" / "search.html"
        self.assertTrue(output.is_file(), "Generated search category page missing")
        html = output.read_text(encoding="utf-8")
        self.assertIn('이 분야의 이용 가이드', html)
        self.assertIn('/blog/seo-20261030-26325b73af/', html)

    def test_directory_landing_has_all_eight_crawlable_categories_with_counts(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        counts = {}
        for record in records:
            counts[record["category"]] = counts.get(record["category"], 0) + 1
        html = (root / "dist/directory.html").read_text(encoding="utf-8")
        nav = re.search(r'<nav aria-label="분야별 사이트모음 바로가기".*?</nav>',
                        html, re.S)
        self.assertIsNotNone(nav)
        from build import CATEGORY_LANDING
        for category, slug, _, _ in CATEGORY_LANDING:
            self.assertIn(f'href="/categories/{slug}"', nav.group())
            self.assertIn(f'{category} {counts[category]}개', nav.group())
        self.assertEqual(nav.group().count('href="/categories/'), len(CATEGORY_LANDING) + 1)

    def test_directory_category_overview_is_grounded_in_registered_sites(self):
        from build import CATEGORY_LANDING, directory_category_overview
        records = [
            {"name": "예시 검색", "category": "검색·포털", "url": "https://example.com"},
            {"name": "예시 커뮤니티", "category": "커뮤니티", "url": "https://example.org"},
            {"name": "<script>위험</script>", "category": "커뮤니티", "url": "https://example.net"},
        ]
        result = directory_category_overview(records, CATEGORY_LANDING)
        self.assertIn("예시 검색", result)
        self.assertIn("예시 커뮤니티", result)
        self.assertIn("등록 사이트 2개", result)
        self.assertIn("예시 검색</strong> —", result)
        self.assertIn("이 분야 전체 등록 사이트 보기", result)
        self.assertIn("&lt;script&gt;위험&lt;/script&gt;", result)
        self.assertNotIn("<script>위험</script>", result)
        self.assertNotIn("검색·포털 97개", result)

    def test_built_directory_renders_all_real_category_examples_without_duplicates(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        html = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('aria-label="분야별 사이트 목록 비교"'), 1)
        overview = html.split('aria-label="분야별 사이트 목록 비교"', 1)[1].split('<section aria-label="안전한 링크 이용"', 1)[0]
        from build import CATEGORY_LANDING
        for category, slug, _, _ in CATEGORY_LANDING:
            expected = next(record["name"] for record in records if record["category"] == category)
            self.assertIn(expected, overview)
            self.assertIn(f'/categories/{slug}', overview)
        self.assertIn('id="v6-results"', html)
        self.assertIn("사이트의 이름과 목록 설명을 비교", html)
        first = next(record for record in records if record["category"] == "검색·포털")
        self.assertIn(first["description"], html)

    def test_post_sitemap_date_comes_from_filename_not_filesystem_mtime(self):
        self.assertEqual(stable_post_lastmod(Path('seo-20261027-9c0ac627e0.md')), '2026-10-27')
        self.assertIsNone(stable_post_lastmod(Path('address-directory-safety-guide.md')))
        self.assertIsNone(stable_post_lastmod(Path('seo-20261377-bad.md')))

    def test_generated_canonical_and_og_use_nonredirecting_url(self):
        html = (
            '<link href="https://linkwiki.info/guides/address-check.html" rel="canonical">'
            '<meta property="og:url" content="https://linkwiki.info/guides/address-check.html">'
            '<a href="/guides/address-check.html">가이드</a>'
        )
        normalized = normalize_page_links(html)
        self.assertIn('href="https://linkwiki.info/guides/address-check" rel="canonical"', normalized)
        self.assertIn('content="https://linkwiki.info/guides/address-check"', normalized)
        self.assertIn('href="/guides/address-check"', normalized)
        self.assertNotIn('address-check.html', normalized)

    def test_category_breadcrumb_schema_uses_real_navigation_hierarchy(self):
        source = '<html><head><title>분야</title></head><body><h1>스포츠 링크모음</h1></body></html>'
        result = add_breadcrumb_data(source, '/categories/sports')
        block = re.search(r'<script type="application/ld\+json">(.*?)</script>', result)
        self.assertIsNotNone(block)
        schema = json.loads(block.group(1))
        self.assertEqual(schema['@type'], 'BreadcrumbList')
        self.assertEqual([entry['name'] for entry in schema['itemListElement']],
                         ['홈', '분야별 사이트', '스포츠 링크모음'])
        self.assertEqual(schema['itemListElement'][-1]['item'],
                         'https://linkwiki.info/categories/sports')

    def test_breadcrumb_schema_skips_home_and_is_idempotent(self):
        source = '<html><head></head><body><h1>주소 확인 방법</h1></body></html>'
        self.assertEqual(add_breadcrumb_data(source, '/'), source)
        result = add_breadcrumb_data(source, '/guides/address-check')
        self.assertEqual(add_breadcrumb_data(result, '/guides/address-check'), result)
        self.assertEqual(result.count('application/ld+json'), 1)

    def test_generated_pages_do_not_show_preview_notice(self):
        html = '<footer>링크위키 · 공개 전 미리보기. 외부 사이트는 별도 운영됩니다.</footer>'
        normalized = normalize_page_links(html)
        self.assertNotIn("공개 전 미리보기", normalized)
        self.assertIn("링크위키 · 사이트 주소와 이용 정보를 안내합니다.", normalized)

    def test_existing_evergreen_guide_titles_are_read(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "guides").mkdir()
            (root / "guides" / "sample.html").write_text(
                '<html><head><title>공식 주소 확인 방법 | 링크위키</title></head></html>',
                encoding="utf-8")
            with patch.object(auto_seo, "ROOT", root):
                self.assertEqual(auto_seo.static_guide_titles(), ["공식 주소 확인 방법"])


if __name__ == "__main__":
    unittest.main()
