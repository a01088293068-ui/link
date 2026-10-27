import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

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

    def test_topic_selection_skips_duplicate(self):
        found = seo.select_topic("주소모음 사이트 선택 기준",
            {"related": ["사이트 접속 오류 해결 방법", "주소모음 사이트 선택 기준"]},
            [], ["주소모음 사이트 선택 기준"])
        self.assertEqual(found, "사이트 접속 오류 해결 방법")

    def test_unrelated_and_blocked_topics(self):
        found = seo.select_topic("링크모음 안전하게 이용하는 방법",
            {"related": ["오늘 날씨", "불법 사이트 주소모음", "링크모음 비교 방법"]}, [], [])
        self.assertIn(found, {"링크모음 비교 방법", "링크모음 안전하게 이용하는 방법"})

    def test_render_and_quality_gate(self):
        article = {"title": "링크모음 사이트 비교 기준", "description": "링크모음 사이트를 비교할 때 실제 연결 주소, 카테고리, 검색 편의성, 운영 주체의 안내와 개인정보 입력 요청을 점검하는 방법을 차근차근 설명합니다.",
            "introduction": "사이트를 비교할 때 확인해야 하는 항목들입니다. " * 8,
            "sections": [{"heading": f"확인 항목 {i}", "paragraphs": ["링크의 실제 이동 주소와 설명을 대조하고 공식 공지를 확인합니다. " * 6,
              "검색창과 카테고리의 정확성을 직접 시험하고 불필요한 권한 요구를 확인합니다. " * 5]} for i in range(4)],
            "faq": [{"question": f"질문 {i}", "answer": "운영 주체와 이용 조건을 직접 확인하고 연결 주소가 공식적으로 안내된 주소인지 비교해 보세요. 불확실하면 접속을 멈추세요."} for i in range(3)]}
        draft = seo.render(article)
        self.assertIn("/directory.html", draft)
        self.assertFalse(seo.deterministic_review("링크모음 사이트 비교 기준", article, draft, []))
        self.assertTrue(seo.deterministic_review("링크모음 사이트 비교 기준", article, draft, [article["title"]]))

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

    def sample_article(self):
        return {"title": "링크모음 사이트 비교 기준",
                "description": "링크모음 사이트를 비교하는 구체적인 기준을 설명하고 안전한 주소 확인 단계와 실수하기 쉬운 점검 방법을 정리한 이용 안내입니다.",
                "introduction": "연결 주소의 정확성과 분류 기준을 확인하는 방법을 설명합니다. " * 8,
                "sections": [{"heading": f"확인 단계 {i}", "paragraphs": ["표시된 도메인을 공식 운영자 안내와 직접 대조합니다. " * 5,
                              "이동하기 전에 입력 요구와 목적지를 신중하게 살펴봅니다. " * 5]} for i in range(4)],
                "faq": [{"question": f"질문 {i}", "answer": "서비스가 안내하는 공식 주소와 운영 정보를 확인하고 이상한 경고가 나타나면 진행을 멈추고 고객센터 안내를 확인하세요."} for i in range(3)]}


if __name__ == "__main__":
    unittest.main()
