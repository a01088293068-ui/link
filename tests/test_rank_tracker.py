import unittest
from seo import rank_tracker


class RankTrackerTests(unittest.TestCase):
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
