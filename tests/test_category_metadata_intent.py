"""Guard category landing metadata against generic fallback copy."""
from pathlib import Path
import re
import unittest
from build import category_hub_metadata

ROOT = Path(__file__).resolve().parents[1]


class CategoryMetadataIntentTests(unittest.TestCase):
    def test_category_hub_metadata_is_specific_and_data_backed(self):
        records = [
            {"name": "포털", "category": "검색·포털"},
            {"name": "공공서비스", "category": "검색·포털"},
            {"name": "한인 커뮤니티", "category": "한인교민"},
        ]
        categories = (
            ("검색·포털", "search", "검색·포털 링크모음", "검색·포털 안내"),
            ("한인교민", "korean", "해외 한인 사이트모음", "한인 정보 안내"),
        )
        title, description, domestic_count, overseas_count = category_hub_metadata(
            records, categories
        )
        self.assertEqual(title, "분야별 링크모음 2개 분야·3개 사이트 | 링크위키")
        self.assertIn("국내 이용 목적 중심 2개", description)
        self.assertIn("해외 한인 정보 1개", description)
        self.assertIn("검색·포털", description)
        self.assertEqual((domestic_count, overseas_count), (2, 1))

    def test_finance_page_targets_korean_finance_link_collection_intent(self):
        source = (ROOT / "categories" / "finance.html").read_text(encoding="utf-8")
        self.assertIn("<title>금융 링크모음·사이트모음 | 은행·금융 정보 - 링크위키</title>", source)
        self.assertIn("<h1>금융 링크모음·사이트모음</h1>", source)
        self.assertIn("금융 링크모음에서 국내 은행 업무", source)
        self.assertRegex(source, r'<link\b(?=[^>]*\brel="canonical")(?=[^>]*\bhref="https://linkwiki\.info/categories/finance")[^>]*>')
        self.assertIn('property="og:title"', source)
        self.assertIn('property="og:description"', source)

    def test_community_page_has_specific_korean_search_intent(self):
        source = (ROOT / "categories" / "community.html").read_text(encoding="utf-8")
        self.assertIn("<title>국내 커뮤니티 사이트모음 | 게임·IT·취미·생활 - 링크위키</title>", source)
        self.assertIn("<h1>국내 커뮤니티 사이트모음: 게임·IT·취미·생활</h1>", source)
        self.assertIn("게임·IT·스포츠·취미·생활·중고거래", source)
        self.assertRegex(source, r'<link\b(?=[^>]*\brel="canonical")(?=[^>]*\bhref="https://linkwiki\.info/categories/community")[^>]*>')
        self.assertIn('property="og:title"', source)
        self.assertIn('property="og:description"', source)

    def test_overseas_korean_page_has_specific_region_search_intent(self):
        source = (ROOT / "categories" / "korean.html").read_text(encoding="utf-8")
        self.assertIn("<title>해외 한인 사이트모음 | 국가별 교민 커뮤니티·생활정보 - 링크위키</title>", source)
        self.assertIn("<h1>해외 한인 사이트모음: 국가별 교민 정보·커뮤니티</h1>", source)
        self.assertIn("국가·지역별 교민 뉴스", source)
        self.assertRegex(source, r'<link\b(?=[^>]*\brel="canonical")(?=[^>]*\bhref="https://linkwiki\.info/categories/korean")[^>]*>')
        self.assertIn('property="og:title"', source)
        self.assertIn('property="og:description"', source)


if __name__ == "__main__":
    unittest.main()
