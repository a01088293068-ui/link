"""Keep the full directory page aligned with its address-search intent."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DirectorySearchIntentTests(unittest.TestCase):
    def test_directory_page_targets_address_search_without_losing_site_collection_context(self):
        html = (ROOT / "directory.html").read_text(encoding="utf-8")
        self.assertIn("<title>주소모음 전체 검색 | 360개 사이트 이름·도메인 찾기 - 링크위키</title>", html)
        self.assertIn('name="description"', html)
        self.assertIn("주소모음에서 360개 사이트를 이름·도메인·13개 분야로 검색하세요.", html)
        self.assertIn('<h1 id="directory-heading">주소모음 전체 검색 · 360개 사이트 이름·도메인 찾기</h1>', html)
        self.assertIn("링크모음·사이트모음 목록", html)
        self.assertIn('href="https://linkwiki.info/directory" rel="canonical"', html)

    def test_directory_page_keeps_indexable_content_and_real_search_catalog(self):
        html = (ROOT / "directory.html").read_text(encoding="utf-8")
        self.assertIn('name="robots"', html)
        self.assertIn('content="index,follow"', html)
        self.assertIn('id="v6-results"', html)
        self.assertIn("등록 사이트 360개", html)


if __name__ == "__main__":
    unittest.main()
