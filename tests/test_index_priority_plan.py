"""Offline tests for evidence-backed SEO work prioritization."""
import unittest
from seo.index_priority_plan import decide, render


class IndexPriorityPlanTests(unittest.TestCase):
    def test_stale_crawl_cannot_prove_latest_release_was_indexed(self):
        state, step = decide({
            "verdict": "PASS",
            "coverage": "Submitted and indexed",
            "last_crawl": "2026-10-29T09:37:37Z",
        }, "2026-11-10")
        self.assertIn("변경 전 크롤링", state)
        self.assertIn("재크롤링", step)

    def test_fresh_crawled_not_indexed_requires_substantive_review(self):
        state, step = decide({
            "verdict": "NEUTRAL",
            "coverage": "Crawled - currently not indexed",
            "last_crawl": "2026-11-12T09:37:37Z",
        }, "2026-11-10")
        self.assertEqual(state, "크롤링 후 미색인")
        self.assertIn("고유 가치", step)

    def test_missing_google_inspection_is_unknown(self):
        state, step = decide(None, "2026-11-10")
        self.assertIn("없음", state)
        self.assertIn("Inspection", step)

    def test_crawl_same_day_is_not_claimed_as_after_edit(self):
        state, step = decide({
            "verdict": "PASS", "last_crawl": "2026-11-10T03:00:00Z",
        }, "2026-11-10")
        self.assertIn("미확정", state)
        self.assertIn("수정 시각", step)

    def test_render_report_keeps_exact_keywords_separate(self):
        sample = {
            "schema": 1, "end_date": "2026-11-07",
            "significant_page_updates": {"/": "2026-11-10", "/directory": "2026-11-10"},
            "inspections": [
                {"url": "https://linkwiki.info/", "verdict": "PASS",
                 "last_crawl": "2026-10-29T09:37:37Z"},
                {"url": "https://linkwiki.info/directory", "verdict": "NEUTRAL",
                 "coverage": "Crawled - currently not indexed",
                 "last_crawl": "2026-11-08T08:29:34Z"},
            ],
            "core_keywords": [
                {"keyword": "주소모음", "observed": True, "impressions": 1,
                 "clicks": 1, "position": 111.0,
                 "pages": ["https://linkwiki.info/"]},
                {"keyword": "링크모음", "observed": True, "impressions": 4,
                 "clicks": 1, "position": 123.0,
                 "pages": ["https://linkwiki.info/"]},
                {"keyword": "사이트모음", "observed": False},
            ],
        }
        output = render(sample)
        self.assertIn("2026-11-07", output)
        self.assertIn("| 주소모음 | 1 | 1 | 111.0 |", output)
        self.assertIn("| 링크모음 | 4 | 1 | 123.0 |", output)
        self.assertIn("| 사이트모음 | 미관측 | - | - |", output)
        self.assertIn("최신 변경 전 크롤링", output)
        self.assertNotIn("색인 성공 확정", output)


if __name__ == "__main__":
    unittest.main()
