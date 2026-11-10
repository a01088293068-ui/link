import unittest

from seo.search_console_monitor import format_core_keyword_index_alignment


class CoreKeywordIndexAlignmentTests(unittest.TestCase):
    def test_observed_impression_does_not_get_labelled_unindexed_absence(self):
        pages = [
            {"keys": ["주소모음", "https://linkwiki.info/"], "impressions": 3},
            {"keys": ["주소모음 추천", "https://linkwiki.info/directory"], "impressions": 9},
        ]
        inspections = [{
            "url": "https://linkwiki.info/",
            "verdict": "NEUTRAL",
            "coverage": "크롤링됨 - 현재 색인이 생성되지 않음",
            "robots_state": "ALLOWED",
            "indexing_state": "INDEXING_ALLOWED",
            "fetch_state": "SUCCESSFUL",
        }]
        result = format_core_keyword_index_alignment(pages, inspections)
        self.assertIn("주소모음 | https://linkwiki.info/ | 3", result)
        self.assertIn("변경 후 재크롤링", result)
        self.assertNotIn("주소모음 추천 |", result)
        self.assertIn("노출된 적이 있는 URL을 색인 상태만으로", result)

    def test_priority_is_actual_technical_obstacle(self):
        pages = [{"keys": ["링크모음", "https://linkwiki.info/directory"],
                  "impressions": 2}]
        inspections = [{
            "url": "https://linkwiki.info/directory",
            "verdict": "FAIL",
            "coverage": "Blocked",
            "robots_state": "DISALLOWED",
        }]
        result = format_core_keyword_index_alignment(pages, inspections)
        self.assertIn("Google robots.txt 차단 확인", result)

    def test_unknown_and_failure_are_not_misrepresented(self):
        pages = [{"keys": ["사이트모음", "https://linkwiki.info/directory"],
                  "impressions": 1}]
        self.assertIn("미조회", format_core_keyword_index_alignment(pages, []))
        self.assertIn("조회 실패", format_core_keyword_index_alignment(pages, [], "HTTP 403"))
        self.assertIn("정확 검색어·페이지 조합 관측 없음",
                      format_core_keyword_index_alignment([], []))


if __name__ == "__main__":
    unittest.main()
