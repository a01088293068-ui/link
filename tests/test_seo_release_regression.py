from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from build import add_breadcrumb_data, normalize_page_links, stable_post_lastmod
import json
import re
from seo import auto_seo


class SEOReleaseRegressionTests(unittest.TestCase):
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
        block = re.search(r'<script type="application/ld\\+json">(.*?)</script>', result)
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
