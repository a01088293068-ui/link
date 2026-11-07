import unittest
from seo import rank_tracker


class RankTrackerTests(unittest.TestCase):
    def test_short_first_serp_page_does_not_hide_second_page(self):
        from unittest.mock import patch
        pages = {
            1: [{"link": f"https://a.example/{n}", "position": n}
                for n in range(1, 10)],
            2: [{"link": "https://linkwiki.info/directory", "position": 12}],
            3: [],
        }
        with patch.object(rank_tracker, "search",
                          side_effect=lambda query, key, page: pages[page]) as fetch:
            results = rank_tracker.search_top_results("주소모음", "test")
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(len(results), 10)
        self.assertEqual(rank_tracker.find_result(results)["position"], 12)
        self.assertEqual(results[-1]["_sample_position"], 12)

    def test_missing_provider_positions_preserve_page_offsets(self):
        from unittest.mock import patch
        pages = {
            1: [{"link": f"https://example.org/{n}", "title": f"Example {n}"} for n in range(9)],
            2: [{"link": "https://linkwiki.info/directory"}],
            3: [],
        }
        with patch.object(rank_tracker, "search",
                          side_effect=lambda query, key, page: pages[page]):
            rows = rank_tracker.search_top_results("링크모음", "test")
        self.assertEqual(rank_tracker.find_result(rows)["position"], 11)
        self.assertEqual(rank_tracker.observed_competitors(rows, limit=10)[0]["position"], 1)

    def test_provider_position_used_after_deduplication(self):
        from unittest.mock import patch
        repeated = [{"link": "https://example.org/a", "position": 1}]
        pages = {
            1: repeated + [{"link": f"https://example.org/{n}", "position": n}
                            for n in range(2, 11)],
            2: repeated + [{"link": "https://linkwiki.info/", "position": 15}],
            3: [],
        }
        with patch.object(rank_tracker, "search",
                          side_effect=lambda query, key, page: pages[page]):
            rows = rank_tracker.search_top_results("사이트모음", "test")
        self.assertEqual(rank_tracker.find_result(rows)["position"], 15)

    def test_paginates_when_provider_caps_each_response_at_ten(self):
        from unittest.mock import patch
        pages = {page: [{"link": f"https://example.org/{(page - 1) * 10 + i}"}
                        for i in range(10)] for page in (1, 2, 3)}
        pages[3][4] = {"link": "https://linkwiki.info/"}
        with patch.object(rank_tracker, "search", side_effect=lambda query, key, page: pages[page]) as fetch:
            rows = rank_tracker.search_top_results("주소모음", "test")
        self.assertEqual(len(rows), 30)
        self.assertEqual(rank_tracker.find_result(rows)["position"], 25)
        self.assertEqual(fetch.call_count, 3)

    def test_repeated_page_does_not_claim_top_thirty(self):
        from unittest.mock import patch
        ten = [{"link": f"https://example.com/{i}"} for i in range(10)]
        with patch.object(rank_tracker, "search", return_value=ten) as fetch:
            rows = rank_tracker.search_top_results("링크모음", "test")
        self.assertEqual(len(rows), 10)
        self.assertEqual(fetch.call_count, 2)

    def test_longtail_queries_use_single_serp_page(self):
        from unittest.mock import patch
        ten = [{"link": f"https://example.com/{i}"} for i in range(10)]
        self.assertEqual(rank_tracker.query_depth("웹툰 링크모음"), 10)
        self.assertEqual(rank_tracker.query_depth("주소모음"), 30)
        with patch.object(rank_tracker, "search", return_value=ten) as fetch:
            rows = rank_tracker.search_top_results("웹툰 링크모음", "test", limit=10)
        self.assertEqual(len(rows), 10)
        fetch.assert_called_once_with("웹툰 링크모음", "test", page=1)

    def test_longtail_has_distinct_existing_page_intents(self):
        self.assertIn("커뮤니티 사이트모음", rank_tracker.KEYWORDS)
        self.assertIn("사이트 주소 확인 방법", rank_tracker.KEYWORDS)
        self.assertEqual(len(rank_tracker.KEYWORDS), len(set(rank_tracker.KEYWORDS)))
        self.assertTrue(set(rank_tracker.CORE_KEYWORDS).isdisjoint(rank_tracker.LONGTAIL_KEYWORDS))

    def test_detect_exact_host_and_subdomain(self):
        results = [
            {"link": "https://other.example.com/"},
            {"link": "https://linkwiki.info/directory.html"},
        ]
        self.assertEqual(rank_tracker.find_result(results)["position"], 2)

    def test_not_confused_by_lookalike(self):
        results = [{"link": "https://fake-linkwiki.info/"},
                   {"link": "https://linkwiki.info.evil.example/"}]
        self.assertIsNone(rank_tracker.find_result(results)["position"])

    def test_partial_provider_results_are_not_a_complete_rank_check(self):
        observations = {'주소모음': {'position': None, 'url': None},
                        '링크모음': {'position': None, 'url': None},
                        '웹툰 링크모음': {'position': None, 'url': None}}
        counts = {'주소모음': 9, '링크모음': 30, '웹툰 링크모음': 10}
        coverage = rank_tracker.coverage_for(observations, counts)
        self.assertEqual(coverage['주소모음'], 'partial')
        self.assertEqual(coverage['링크모음'], 'complete')
        self.assertEqual(coverage['웹툰 링크모음'], 'complete')

    def test_primary_scorecard_distinguishes_confirmed_and_partial_absence(self):
        history = {"samples": [
            {"date": "2026-11-06",
             "results": {"주소모음": {"position": None}, "링크모음": {"position": None},
                         "사이트모음": {"position": None}},
             "returned_results": {"주소모음": 9, "링크모음": 30, "사이트모음": 30},
             "sample_coverage": {"주소모음": "partial", "링크모음": "complete",
                                 "사이트모음": "complete"}},
            {"date": "2026-11-07",
             "results": {"주소모음": {"position": None}, "링크모음": {"position": 19,
                "url": "https://linkwiki.info/directory"}, "사이트모음": {"position": None}},
             "returned_results": {"주소모음": 9, "링크모음": 30, "사이트모음": 30},
             "sample_coverage": {"주소모음": "partial", "링크모음": "complete",
                                 "사이트모음": "complete"}}
        ]}
        report = rank_tracker.core_keyword_scorecard(history)
        self.assertIn("| 주소모음 | 표본 미발견 · 30위 내 여부 미확정 | 9/30 |", report)
        self.assertIn("링크모음 | 19위", report)
        self.assertIn("| 사이트모음 | 검사한 상위 30개에서 미발견 | 30/30 |", report)
        self.assertIn("직전 측정", report)
        self.assertIn("2026-11-07", report)
        self.assertNotIn("주소모음 | 30위 밖", report)

    def test_primary_scorecard_without_samples_does_not_invent_results(self):
        report = rank_tracker.core_keyword_scorecard({"samples": []})
        self.assertIn("측정일: 데이터 없음", report)
        self.assertIn("| 주소모음 | 데이터 없음", report)

    def test_competitor_capture_uses_real_titles_and_excludes_own_domain(self):
        rows = [
            {"link": "https://linkwiki.info/directory", "title": "My own site"},
            {"link": "https://address-example.kr/", "title": "주소모음 최신 사이트"},
            {"link": "http://plain.example/", "title": "Insecure"},
            {"link": "https://linkwiki.info.evil.test/", "title": "Unrelated hostname"},
            {"link": "https://another.example/path", "title": "사이트모음 한눈에"},
        ]
        results = rank_tracker.observed_competitors(rows, limit=2)
        self.assertEqual([r["position"] for r in results], [2, 4])
        self.assertEqual(results[0]["title"], "주소모음 최신 사이트")
        self.assertNotIn("linkwiki.info/directory", str(results))

    def test_competitor_report_is_observed_data_not_guessed_ranks(self):
        sample = {
            "date": "2026-11-07",
            "returned_results": {"주소모음": 30, "링크모음": 9},
            "sample_coverage": {"주소모음": "complete", "링크모음": "partial"},
            "competitor_top": {
                "주소모음": [
                    {"position": 1, "title": "주소모음 | 첫번째", "url": "https://example.org/"}
                ]
            }
        }
        report = rank_tracker.competitor_report({"samples": [sample]})
        self.assertIn("측정일: 2026-11-07", report)
        self.assertIn("| 1 | 주소모음 \| 첫번째 | https://example.org/ |", report)
        self.assertIn("검사한 자연 검색 결과: 9/30개", report)
        self.assertIn("관측 데이터 없음", report)
        self.assertNotIn("도메인 권위: 95", report)

    def test_competitor_report_empty_history_is_explicitly_unknown(self):
        report = rank_tracker.competitor_report({"samples": []})
        self.assertIn("측정일: 데이터 없음", report)
        self.assertEqual(report.count("관측 데이터 없음"), 3)

    def test_missing_is_not_a_false_rank(self):
        result = rank_tracker.find_result([])
        self.assertEqual(result, {"position": None, "url": None})

    def test_collect_keeps_each_query(self):
        result = rank_tracker.collect(lambda _: [{"link": "https://linkwiki.info/"}],
                                      queries=("링크모음", "주소모음"))
        self.assertEqual(set(result), {"링크모음", "주소모음"})
        self.assertEqual(result["주소모음"]["position"], 1)


if __name__ == "__main__":
    unittest.main()
