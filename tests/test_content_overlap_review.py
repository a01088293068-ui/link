"""Validate audit avoids inventing Google duplication or deleting live SEO guides."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from seo.content_overlap_review import analyze, normalize, render


class ContentOverlapAuditTests(unittest.TestCase):
    def create(self, folder, slug, paragraphs):
        body = "# " + slug + "\n\n" + "\n\n".join(paragraphs) + "\n"
        (folder / (slug + ".md")).write_text(body, encoding="utf-8")

    def test_detect_near_duplicate_bodies_not_just_titles(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            shared = "공식 사이트의 도메인과 운영 주체를 비교하고 주소 변경 시 확인 근거를 기록합니다. " * 8
            distinct = "우체국 택배 접수 기준과 배송 조회 항목의 이름을 확인해야 합니다. " * 9
            self.create(root, "seo-address-intent-a", [shared, shared + "공식 출처."])
            self.create(root, "seo-address-intent-b", [shared, shared + "추가 확인."])
            self.create(root, "seo-unrelated", [distinct, distinct + "별도 작업."])
            result = analyze(root)
        self.assertEqual(result["article_count"], 3)
        self.assertEqual(result["pairs_compared"], 3)
        self.assertEqual(len(result["review_candidates"]), 1)
        pair = result["review_candidates"][0]
        self.assertEqual({pair["a"], pair["b"]},
                         {"seo-address-intent-a", "seo-address-intent-b"})
        self.assertGreaterEqual(pair["body_shingle_jaccard"], 0.36)

    def test_shared_boilerplate_does_not_create_false_duplicate(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            common = "링크위키 등록 정보는 외부 사이트의 실시간 안전성을 보증하지 않습니다. " * 6
            for i, domain in enumerate(["세금 신고", "기차 시간", "공공 도서"]):
                text = (domain + " 목적에 맞는 공식 자료에서 기능을 확인해야 합니다. ") * 15
                self.create(root, "seo-article-" + str(i), [common, text])
            result = analyze(root)
        self.assertEqual(len(result["review_candidates"]), 0)
        self.assertGreaterEqual(len(result["repeated_boilerplate"]), 1)

    def test_draft_or_empty_markdown_excluded(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            self.create(root, "seo-long", ["개별 사이트의 공식 도메인 정보 기준 설명입니다. " * 15])
            (root / "seo-empty.md").write_text("# 제목", encoding="utf-8")
            (root / "notes.md").write_text("Random notes " * 100, encoding="utf-8")
            result = analyze(root)
        self.assertEqual(result["article_count"], 1)

    def test_report_never_uses_google_penalty_language(self):
        with TemporaryDirectory() as t:
            root = Path(t)
            self.create(root, "seo-long", ["카테고리별 제공 서비스 목적 안내입니다. " * 18])
            report = render(analyze(root))
        self.assertIn("편집 검토", report)
        self.assertIn("대량 삭제하지 않습니다", report)
        self.assertNotIn("Google에서 중복 판정 확정", report)

    def test_normalizer_keeps_readable_korean_and_link_label(self):
        text = normalize("# **주소모음** [공식 도메인](https://example.org/) 확인")
        self.assertIn("주소모음", text)
        self.assertIn("공식 도메인", text)
        self.assertNotIn("https://example.org", text)

    def test_no_articles_fails_instead_of_claiming_zero_duplication(self):
        with TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "no published Markdown"):
                analyze(Path(t))


if __name__ == "__main__":
    unittest.main()
