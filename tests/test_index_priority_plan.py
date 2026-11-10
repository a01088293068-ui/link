"""Offline tests for evidence-backed SEO work prioritization."""
import unittest
from seo.index_priority_plan import decide, render, historic_canonical_mismatches, sitemap_diagnostic


class IndexPriorityPlanTests(unittest.TestCase):
    def test_historic_html_canonical_mismatch_is_not_live_failure(self):
        records = [{"url": "https://linkwiki.info/categories/ai",
                    "user_canonical": "https://linkwiki.info/categories/ai.html",
                    "google_canonical": "https://linkwiki.info/categories/ai",
                    "last_crawl": "2026-10-16T06:08:11Z"}]
        mismatches = historic_canonical_mismatches(records)
        self.assertEqual(len(mismatches), 1)
        report = render({"schema": 1, "inspections": records})
        self.assertIn("과거 Google 크롤링", report)
        self.assertIn("categories/ai.html", report)
        self.assertIn("최신 배포본의 문제라고 단정할 수 없습니다", report)

    def test_pending_google_sitemap_is_not_confused_with_public_http(self):
        rows = [
            {"path": "https://linkwiki.info/sitemap.xml",
             "isPending": True, "errors": "0"},
            {"path": "https://linkwiki.info/sitemap-v2.xml",
             "isPending": False, "lastDownloaded": "2026-10-24T04:49:41Z",
             "errors": "0"}]
        result = "\\n".join(sitemap_diagnostic(rows))
        self.assertIn("기본 사이트맵은 Google 처리 완료가 아직 확인되지 않습니다", result)
        self.assertIn("2026-10-24", result)
        self.assertNotIn("처리 오류 1", result)

    def test_failed_sitemap_api_does_not_claim_missing_submission(self):
        result = "\\n".join(sitemap_diagnostic([], "HTTP 403"))
        self.assertIn("API 오류", result)
        self.assertNotIn("제출 기록 미관측", result)

    def test_stale_crawl_cannot_prove_latest_release_was_indexed(self):
        state, freshness, step = decide({
            "verdict": "PASS",
            "coverage": "Submitted and indexed",
            "last_crawl": "2026-10-29T09:37:37Z",
        }, "2026-11-10")
        self.assertEqual(state, "색인됨")
        self.assertIn("변경 전 크롤링", freshness)
        self.assertIn("재크롤링", step)

    def test_fresh_crawled_not_indexed_requires_substantive_review(self):
        state, freshness, step = decide({
            "verdict": "NEUTRAL",
            "coverage": "Crawled - currently not indexed",
            "last_crawl": "2026-11-12T09:37:37Z",
        }, "2026-11-10")
        self.assertEqual(state, "크롤링 후 미색인")
        self.assertIn("고유 가치", step)

    def test_missing_google_inspection_is_unknown(self):
        state, freshness, step = decide(None, "2026-11-10")
        self.assertIn("없음", state)
        self.assertIn("Inspection", step)

    def test_crawl_same_day_is_not_claimed_as_after_edit(self):
        state, freshness, step = decide({
            "verdict": "PASS", "last_crawl": "2026-11-10T03:00:00Z",
        }, "2026-11-10")
        self.assertIn("미확정", freshness)
        self.assertIn("수정 시각", step)

    def test_stale_nonindexed_page_retains_both_findings(self):
        state, freshness, step = decide({
            "verdict": "NEUTRAL", "coverage": "Crawled - currently not indexed",
            "last_crawl": "2026-11-08T08:29:34Z",
        }, "2026-11-10")
        self.assertEqual(state, "크롤링 후 미색인")
        self.assertEqual(freshness, "최근 변경 전 크롤링")
        self.assertIn("재크롤링", step)

    def test_korea_weekly_reporting_is_distinct_from_global_ranks(self):
        record = {
            "schema": 1, "end_date": "2026-11-07",
            "core_keywords": [
                {"keyword": "주소모음", "observed": True,
                 "position": 111.0, "impressions": 1, "clicks": 1,
                 "pages": ["https://linkwiki.info/"]}
            ],
            "korea_core_weekly": [
                {"keyword": "주소모음",
                 "previous": {"observed": True, "impressions": 1,
                              "clicks": 0, "position": 140.0},
                 "recent": {"observed": True, "impressions": 2,
                            "clicks": 1, "position": 90.5}},
            ],
        }
        output = render(record)
        self.assertIn("| 주소모음 | 1 | 1 | 111.0 |", output)
        self.assertIn("| 주소모음 | 1 / 0 / 140.0 | 2 / 1 / 90.5 |", output)
        self.assertIn("대한민국(kor)", output)

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
        self.assertIn("최근 변경 전 크롤링", output)
        self.assertIn("크롤링 후 미색인", output)
        self.assertNotIn("색인 성공 확정", output)


if __name__ == "__main__":
    unittest.main()
