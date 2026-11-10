"""Validate safe accessible comparison tables and directory-to-guide paths."""
import unittest
from pathlib import Path
from build import markdown

ROOT = Path(__file__).resolve().parents[1]

class GuideTableAndRoutesTests(unittest.TestCase):
    def test_markdown_table_is_semantic_and_escaped(self):
        raw = (
            "Before the table.\n\n"
            "| 작업 | 도구 | 메모 |\n"
            "|---|---|---|\n"
            "| 교육 | [EBSi](https://www.ebsi.co.kr/) | <script>alert(1)</script> |\n"
            "| 번역 | DeepL | 문서 검토 |\n\n"
            "After the table.\n"
        )
        html = markdown(raw)
        self.assertIn('<table><thead><tr><th scope="col">작업</th>', html)
        self.assertEqual(html.count("<tr>"), 3)
        self.assertEqual(html.count("<td>"), 6)
        self.assertIn('href="https://www.ebsi.co.kr/"', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("<p>Before the table.</p>", html)
        self.assertIn("<p>After the table.</p>", html)

    def test_pipe_prose_and_malformed_tables_are_not_swallowed(self):
        html = markdown("| left | right |\n| this is not a delimiter |\nNext.")
        self.assertNotIn("<table>", html)
        self.assertIn("this is not a delimiter", html)
        self.assertIn("Next.", html)

    def test_existing_markdown_headings_and_lists_still_render(self):
        html = markdown("## 제목\n\n1. 첫 단계\n2. 두번째 단계\n\n- 확인\n")
        self.assertIn("<h2>제목</h2>", html)
        self.assertIn("<ol>", html)
        self.assertIn("<ul>", html)

    def test_generated_ai_and_education_guides_are_linked_and_sitemapped(self):
        dist = ROOT / "dist"
        mapping = (
            ("seo-20261110-korean-ai-tools-by-task-guide", "ai"),
            ("seo-20261110-korean-education-sites-guide", "search"),
        )
        sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
        for slug, category in mapping:
            with self.subTest(slug=slug):
                article = dist / "blog" / slug / "index.html"
                self.assertTrue(article.is_file())
                content = article.read_text(encoding="utf-8")
                self.assertIn('href="https://linkwiki.info/blog/' + slug + '/"', content)
                self.assertIn("<h1>", content)
                self.assertIn("<h2>", content)
                self.assertIn('<loc>https://linkwiki.info/blog/' + slug + '/</loc>', sitemap)
                cat = (dist / "categories" / (category + ".html")).read_text(encoding="utf-8")
                self.assertIn('href="/blog/' + slug + '/"', cat)
        ai = (dist / "blog/seo-20261110-korean-ai-tools-by-task-guide/index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="blog-table-scroll"><table>', ai)
        self.assertIn('<th scope="col">내가 하려는 일</th>', ai)
        self.assertGreaterEqual(ai.count("<td>"), 18)

if __name__ == "__main__":
    unittest.main()
