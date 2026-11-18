"""Guard category landing metadata against generic fallback copy."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CategoryMetadataIntentTests(unittest.TestCase):
    def test_finance_page_targets_korean_finance_link_collection_intent(self):
        source = (ROOT / "categories" / "finance.html").read_text(encoding="utf-8")
        self.assertIn("<title>금융 링크모음·사이트모음 | 은행·금융 정보 - 링크위키</title>", source)
        self.assertIn("<h1>금융 링크모음·사이트모음</h1>", source)
        self.assertIn("금융 링크모음에서 국내 은행 업무", source)
        self.assertIn('rel="canonical" href="https://linkwiki.info/categories/finance"', source)
        self.assertIn('property="og:title"', source)
        self.assertIn('property="og:description"', source)

    def test_community_page_has_specific_korean_search_intent(self):
        source = (ROOT / "categories" / "community.html").read_text(encoding="utf-8")
        self.assertIn("<title>국내 커뮤니티 사이트모음 | 게임·IT·취미·생활 - 링크위키</title>", source)
        self.assertIn("<h1>국내 커뮤니티 사이트모음: 게임·IT·취미·생활</h1>", source)
        self.assertIn("게임·IT·스포츠·취미·생활·중고거래", source)
        self.assertIn('href="https://linkwiki.info/categories/community" rel="canonical"', source)
        self.assertIn('property="og:title"', source)
        self.assertIn('property="og:description"', source)

    def test_overseas_korean_page_has_specific_region_search_intent(self):
        source = (ROOT / "categories" / "korean.html").read_text(encoding="utf-8")
        self.assertIn("<title>해외 한인 사이트모음 | 국가별 교민 커뮤니티·생활정보 - 링크위키</title>", source)
        self.assertIn("<h1>해외 한인 사이트모음: 국가별 교민 정보·커뮤니티</h1>", source)
        self.assertIn("국가·지역별 교민 뉴스", source)
        self.assertIn('href="https://linkwiki.info/categories/korean" rel="canonical"', source)
        self.assertIn('property="og:title"', source)
        self.assertIn('property="og:description"', source)


if __name__ == "__main__":
    unittest.main()
