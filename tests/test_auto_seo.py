import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).resolve().parents[1] / "seo" / "auto_seo.py"
spec = importlib.util.spec_from_file_location("auto_seo_test", SCRIPT)
seo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seo)


class SEOTests(unittest.TestCase):
    def test_gemini_request_and_json(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(seo, "api_json", return_value={"candidates": [{"content": {"parts": [{"text": '{"pass": true}'}]}}]}) as request:
            self.assertEqual(seo.gemini_json("editor", {"title": "test"}), {"pass": True})
            self.assertIn("gemini-3.8-flash:generateContent", request.call_args.args[0])
            self.assertEqual(request.call_args.args[1]["x-goog-api-key"], "test-key")

    def test_provider_routes_to_gemini(self):
        with patch.dict("os.environ", {"SEO_AI_PROVIDER": "gemini"}), patch.object(seo, "gemini_json", return_value={"ok": True}):
            self.assertEqual(seo.model_json("system", {}), {"ok": True})

    def test_gemini_transient_retry(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(seo, "api_json", side_effect=[RuntimeError("API HTTP 503: unavailable"), {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}]) as request, patch.object(seo.time, "sleep"):
            self.assertEqual(seo.gemini_json("system", {}), {"ok": True})
            self.assertEqual(request.call_count, 2)

    def test_gemini_retries_same_model_up_to_five_times(self):
        success = {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(seo, "api_json", side_effect=[RuntimeError("API HTTP 503: overloaded")] * 4 + [success]) as request, patch.object(seo.time, "sleep") as pause:
            self.assertEqual(seo.gemini_json("system", {}), {"ok": True})
            self.assertEqual(request.call_count, 5)
            self.assertEqual([call.args[0] for call in pause.call_args_list], [5, 10, 20, 40])
            self.assertTrue(all("gemini-3.8-flash" in call.args[0] for call in request.call_args_list))

    def test_timeout_is_retried(self):
        success = {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(seo, "api_json", side_effect=[RuntimeError("API network error: The read operation timed out"), success]) as request, patch.object(seo.time, "sleep"):
            self.assertEqual(seo.gemini_json("system", {}), {"ok": True})
            self.assertEqual(request.call_count, 2)

    def test_exhausted_retries_stop(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(seo, "api_json", side_effect=RuntimeError("API HTTP 503: overloaded")) as request, patch.object(seo.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "503"):
                seo.gemini_json("system", {})
            self.assertEqual(request.call_count, 5)

    def test_nontransient_not_retried(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), patch.object(seo, "api_json", side_effect=RuntimeError("API HTTP 403: forbidden")) as request, patch.object(seo.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "403"):
                seo.gemini_json("system", {})
            self.assertEqual(request.call_count, 1)
    def test_similarity(self):
        self.assertGreater(seo.similarity("주소모음 사이트 선택 기준", "주소모음 사이트 선택기준"), .9)

    def test_seed_topics_cover_distinct_real_directory_categories(self):
        seeds = [line.strip() for line in seo.SEEDS.read_text(encoding='utf-8').splitlines()
                 if line.strip() and not line.startswith('#')]
        self.assertEqual(len(seeds), len(set(seeds)))
        for subject in ('커뮤니티', '한인', 'AI 도구', '스포츠', '웹툰', 'OTT', '포털'):
            self.assertTrue(any(subject in topic for topic in seeds), subject)

    def test_topic_selection_skips_duplicate(self):
        found = seo.select_topic("주소모음 사이트 선택 기준",
            {"related": ["사이트 접속 오류 해결 방법", "주소모음 사이트 선택 기준"]},
            [], ["주소모음 사이트 선택 기준"])
        self.assertEqual(found, "사이트 접속 오류 해결 방법")

    def test_unrelated_and_blocked_topics(self):
        found = seo.select_topic("링크모음 안전하게 이용하는 방법",
            {"related": ["오늘 날씨", "불법 사이트 주소모음", "링크모음 비교 방법"]}, [], [])
        self.assertIn(found, {"링크모음 비교 방법", "링크모음 안전하게 이용하는 방법"})

    def test_selection_uses_serp_title_signal_without_extra_api_calls(self):
        research = {"related": ["사이트 접속 오류 해결 방법"], "organic": [
            {"title": "주소모음 사이트 선택 기준", "link": "https://example.org/a"},
            {"title": "주소모음 사이트 선택 기준 안내", "link": "https://other.org/a"},
            {"title": "주소모음 사이트 선택 기준 정리", "link": "https://third.org/a"}]}
        self.assertEqual(seo.select_topic("주소모음 사이트 선택 기준", research, [], []),
                         "사이트 접속 오류 해결 방법")

    def test_related_posts_link_only_existing_published_paths(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "good-entry.md").write_text("# 링크모음 접속 오류 해결 방법\n", encoding="utf-8")
            (directory / "unrelated.md").write_text("# 구매 상품 배송 추적\n", encoding="utf-8")
            (directory / "not-a-post.txt").write_text("# 링크모음 접속 오류 해결 방법", encoding="utf-8")
            with patch.object(seo, "CONTENT", directory):
                links = seo.related_posts("링크모음 접속 오류 해결")
        self.assertEqual(links, [("링크모음 접속 오류 해결 방법", "/blog/good-entry/")])
        self.assertIn("/blog/good-entry/", seo.render(self.sample_article(), links))
        self.assertNotIn("/blog/unrelated/", seo.render(self.sample_article(), links))

    def test_render_rejects_unexpected_related_post_paths(self):
        article = self.sample_article()
        rendered = seo.render(article, [("외부", "https://untrusted.invalid/"), ("정상", "/blog/valid-post/")])
        self.assertNotIn("untrusted.invalid", rendered)
        self.assertIn("/blog/valid-post/", rendered)

    def test_render_and_quality_gate(self):
        article = {"title": "링크모음 사이트 비교 기준", "description": "링크모음 사이트를 비교할 때 실제 연결 주소, 카테고리, 검색 편의성, 운영 주체의 안내와 개인정보 입력 요청을 점검하는 방법을 차근차근 설명합니다.",
            "introduction": "사이트를 비교할 때 확인해야 하는 항목들입니다. " * 8,
            "sections": [{"heading": f"확인 항목 {i}", "paragraphs": [
                self.unique_paragraphs()[i * 2] * 3,
                self.unique_paragraphs()[i * 2 + 1] * 3]} for i in range(4)],
            "faq": [{"question": f"질문 {i}", "answer": "운영 주체와 이용 조건을 직접 확인하고 연결 주소가 공식적으로 안내된 주소인지 비교해 보세요. 불확실하면 접속을 멈추세요."} for i in range(3)]}
        draft = seo.render(article)
        self.assertIn("/directory.html", draft)
        self.assertIn("[링크위키 주소모음·링크모음 홈](/)", draft)
        self.assertFalse(seo.deterministic_review("링크모음 사이트 비교 기준", article, draft, []))
        self.assertTrue(seo.deterministic_review("링크모음 사이트 비교 기준", article, draft, [article["title"]]))

    def test_repeated_paragraphs_within_one_article_are_rejected(self):
        article = self.sample_article()
        article["sections"][1]["paragraphs"][0] = article["sections"][0]["paragraphs"][0]
        issues = seo.deterministic_review("링크모음 사이트 비교 기준", article, seo.render(article), [])
        self.assertIn("repetitive paragraphs within article", issues)

    def test_repeated_headings_within_one_article_are_rejected(self):
        article = self.sample_article()
        article["sections"][1]["heading"] = article["sections"][0]["heading"]
        issues = seo.deterministic_review("링크모음 사이트 비교 기준", article, seo.render(article), [])
        self.assertIn("repetitive section or FAQ headings", issues)

    def test_unsafe_bulk_cookie_deletion_advice_is_rejected(self):
        article = self.sample_article()
        article["sections"][0]["paragraphs"][0] += " 모든 쿠키를 삭제하세요."
        issues = seo.deterministic_review("링크모음 사이트 비교 기준", article, seo.render(article), [])
        self.assertIn("potentially unsafe troubleshooting advice", issues)

    def test_warning_about_bulk_deletion_is_not_rejected(self):
        article = self.sample_article()
        article["sections"][0]["paragraphs"][0] += " 전체 쿠키를 삭제하면 로그아웃될 수 있습니다."
        issues = seo.deterministic_review("링크모음 사이트 비교 기준", article, seo.render(article), [])
        self.assertNotIn("potentially unsafe troubleshooting advice", issues)

    def test_off_topic_multi_search_drift_is_rejected(self):
        article = self.sample_article()
        article["sections"][0]["paragraphs"][0] += " 브라우저 멀티검색 기능을 사용하는 방법도 알아봅니다."
        issues = seo.deterministic_review("주소모음 사이트 검색 방법", article, seo.render(article), [])
        self.assertIn("unrelated multi-search feature drift", issues)

    def test_topic_explicitly_about_multi_search_is_not_blocked(self):
        article = self.sample_article()
        article["sections"][0]["paragraphs"][0] += " 멀티검색 기능의 차이를 알아봅니다."
        issues = seo.deterministic_review("멀티검색 링크모음 비교 방법", article, seo.render(article), [])
        self.assertNotIn("unrelated multi-search feature drift", issues)

    def unique_paragraphs(self):
        return [
                "표시된 도메인의 철자를 먼저 읽고 사이트 운영자가 공지한 주소와 대조해 피싱 징후를 구분합니다.",
                "검색 결과가 원하는 분야를 제대로 반환하는지 다른 표현을 입력해 보고 선택 기준을 기록합니다.",
                "사이트 목록의 분류 체계가 실제 서비스와 일치하는지 여러 항목을 열어 직접 확인합니다.",
                "광고 표시와 일반 링크가 구별되는지 살피고 예상하지 못한 결제 페이지에서는 중단합니다.",
                "모바일 환경에서 메뉴 탐색이 가능한지 확인하되 기기별 배치 차이를 고려합니다.",
                "개인정보 입력을 요구하는 페이지에서는 요청 목적과 운영 정책을 먼저 검토합니다.",
                "접속 오류가 발생하면 현재 도메인과 이전에 저장한 즐겨찾기 주소의 차이를 비교합니다.",
                "유사한 이름의 서비스를 혼동하지 않도록 운영 주체와 공식 안내 채널을 확인합니다."
        ]

    def sample_article(self):
        return {"title": "링크모음 사이트 비교 기준",
                "description": "링크모음 사이트를 비교하는 구체적인 기준을 설명하고 안전한 주소 확인 단계와 실수하기 쉬운 점검 방법을 정리한 이용 안내입니다.",
                "introduction": "연결 주소의 정확성과 분류 기준을 확인하는 방법을 설명합니다. " * 8,
                "sections": [{"heading": f"확인 단계 {i}", "paragraphs": [
                    self.unique_paragraphs()[i * 2] * 3,
                    self.unique_paragraphs()[i * 2 + 1] * 3]} for i in range(4)],
                "faq": [{"question": f"질문 {i}", "answer": "서비스가 안내하는 공식 주소와 운영 정보를 확인하고 이상한 경고가 나타나면 진행을 멈추고 고객센터 안내를 확인하세요."} for i in range(3)]}


if __name__ == "__main__":
    unittest.main()
