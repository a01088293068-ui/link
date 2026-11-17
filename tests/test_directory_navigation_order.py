"""Keep directory category navigation aligned with the Korea-first catalog order."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DirectoryNavigationOrderTests(unittest.TestCase):
    def test_interactive_filters_follow_korea_first_category_landing(self):
        source = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        match = re.search(r"const categories = \['전체', (.*?)\];", source, re.S)
        self.assertIsNotNone(match)
        categories = re.findall(r"'([^']+)'", match.group(1))
        self.assertEqual(categories, [
            "검색·포털", "금융·경제", "교육·취업", "생활·교통·여행",
            "쇼핑·가격비교", "뉴스·언론", "커뮤니티", "AI 도구", "스포츠",
            "영상·OTT", "만화·웹툰", "만화", "한인교민",
        ])

    def test_static_quick_links_lead_with_domestic_utility_categories(self):
        source = (ROOT / "directory.html").read_text(encoding="utf-8")
        match = re.search(
            r'<nav aria-label="분야별 사이트모음 바로가기" class="lw-guide-nav">(.*?)</nav>',
            source, re.S)
        self.assertIsNotNone(match)
        links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', match.group(1))
        self.assertEqual(links, [
            ("/categories/search", "검색·포털"),
            ("/categories/finance", "금융·경제"),
            ("/categories/education", "교육·취업"),
            ("/categories/travel", "생활·교통·여행"),
            ("/categories/shopping", "쇼핑·가격비교"),
            ("/categories/news", "뉴스·언론"),
            ("/categories/", "전체 분야 보기"),
        ])



    def test_homepage_shortcuts_prioritize_korean_public_utility_services(self):
        source = (ROOT / "build.py").read_text(encoding="utf-8")
        match = re.search(r"KOREAN_FIRST_SEARCH_NAMES = \\((.*?)\\n\\)", source, re.S)
        self.assertIsNotNone(match)
        names = re.findall(r'"([^"]+)"', match.group(1))
        self.assertEqual(names[:12], [
            "정부24", "국민신문고", "국가법령정보센터", "고용24", "복지로",
            "국민건강보험공단", "국민연금공단", "건강보험심사평가원",
            "국가건강정보포털", "위택스", "국세청 홈택스", "기상청 날씨누리",
        ])

if __name__ == "__main__":
    unittest.main()
