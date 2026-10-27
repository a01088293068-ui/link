import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "seo" / "auto_seo.py"
spec = importlib.util.spec_from_file_location("auto_seo_test", SCRIPT)
seo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seo)


class SEOTests(unittest.TestCase):
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
            "faq": [{"question": f"질문 {i}", "answer": "운영 주체와 이용 조건을 직접 확인하세요."} for i in range(3)]}
        draft = seo.render(article)
        self.assertIn("/directory.html", draft)
        self.assertFalse(seo.deterministic_review("링크모음 사이트 비교 기준", article, draft, []))
        self.assertTrue(seo.deterministic_review("링크모음 사이트 비교 기준", article, draft, [article["title"]]))


if __name__ == "__main__":
    unittest.main()
