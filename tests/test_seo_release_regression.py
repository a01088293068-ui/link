from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from build import normalize_page_links
from seo import auto_seo


class SEOReleaseRegressionTests(unittest.TestCase):
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
