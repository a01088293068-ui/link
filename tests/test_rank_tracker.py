import unittest
from seo import rank_tracker


class RankTrackerTests(unittest.TestCase):
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
