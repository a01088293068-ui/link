"""Guard editorial evidence, accessible tables and honest authoring rules."""
import importlib.util
import json
import re
from pathlib import Path
import unittest

from build import markdown

ROOT = Path(__file__).resolve().parents[1]
SLUGS = (
    "seo-20261111-address-directory-no-results",
    "seo-20261111-mobile-address-directory-check",
    "seo-20261111-site-directory-selection-by-purpose",
)


def module():
    spec = importlib.util.spec_from_file_location("auto_seo_evidence_test", ROOT / "seo" / "auto_seo.py")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class EvidenceAndFormatTests(unittest.TestCase):
    def test_three_articles_have_distinct_tables_and_checklists(self):
        registered = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        self.assertEqual(len(registered), 315)
        distinct_headers = []
        for slug in SLUGS:
            with self.subTest(slug=slug):
                text = (ROOT / "content" / (slug + ".md")).read_text(encoding="utf-8")
                self.assertIn("2026년 11월 11일", text)
                # A dated November 11 article preserves its historical 222-site
                # snapshot; it is not a live catalog-count assertion.
                self.assertIn("222개", text)
                self.assertNotIn("직접 사용해 봤", text)
                self.assertNotIn("직접 실패했", text)
                self.assertIn("|---|---|---|", text)
                self.assertGreaterEqual(text.count("- [ ] "), 4)
                html = markdown(text)
                self.assertIn('<table><thead><tr>', html)
                self.assertIn('<th scope="col">', html)
                self.assertGreaterEqual(html.count("<td>"), 12)
                distinct_headers.append(next(line for line in text.splitlines()
                                             if line.startswith("| ") and " | " in line))
        self.assertEqual(len(set(distinct_headers)), 3)

    def test_autowriter_emits_structured_table_and_tasks_without_claimed_testing(self):
        seo = module()
        article = {
            "title": "주소모음 확인 절차",
            "introduction": "목적별로 검색어를 선택합니다.",
            "sections": [{"heading": "실제 검색", "paragraphs": ["검색어를 확인합니다."]}],
            "faq": [],
            "decision_table": {
                "headers": ["상황", "확인", "다음 행동"],
                "rows": [["이름 확인", "도메인 확인", "공식 주소 비교"],
                         ["목록 검색", "분야 확인", "기능 비교"],
                         ["페이지 오류", "링크 확인", "지원 안내 확인"]]
            },
            "checklist": [
                "검색어와 서비스 이름을 구분했나요?",
                "공식 도메인을 비교하여 확인했나요?",
                "변경된 링크를 무조건 신뢰하지 않았나요?"
            ],
        }
        text = seo.render(article)
        self.assertIn("## 상황별 비교표", text)
        self.assertIn("| 상황 | 확인 | 다음 행동 |", text)
        self.assertIn("## 실천 체크리스트", text)
        self.assertIn("- 공식 도메인을 비교하여 확인했나요?", text)
        self.assertNotIn("직접 테스트", text)
        self.assertIn("<table>", markdown(text))

    def test_bad_structured_data_is_rejected(self):
        seo = module()
        article = {"title": "주소모음", "description": "예시", "introduction": "소개",
                   "sections": [], "faq": [],
                   "decision_table": {"headers": ["하나"], "rows": []},
                   "checklist": ["짧음"]}
        reasons = seo.deterministic_review("주소모음", article, seo.render(article), [])
        self.assertIn("decision table incomplete or unsupported", reasons)
        self.assertIn("action checklist incomplete", reasons)

    def test_generated_pages_contain_accessible_tables(self):
        dist = ROOT / "dist"
        if not dist.exists():
            self.skipTest("Build before evaluating generated HTML")
        for slug in SLUGS:
            with self.subTest(slug=slug):
                html = (dist / "blog" / slug / "index.html").read_text(encoding="utf-8")
                self.assertIn('<div class="blog-table-scroll"><table>', html)
                self.assertIn("<tbody>", html)
                self.assertIn("2026년 11월 11일", html)


if __name__ == "__main__":
    unittest.main()
