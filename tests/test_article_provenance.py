"""Editorial transparency and factual article publisher metadata regression tests."""
from pathlib import Path
import json
import re
import unittest

from build import article_provenance

ROOT = Path(__file__).resolve().parents[1]


class ArticleProvenanceTests(unittest.TestCase):
    def test_schema_is_factual_and_canonical(self):
        url = "https://linkwiki.info/blog/example/"
        note, script = article_provenance("주소모음 실제 이용 가이드", url, "2026-11-11")
        self.assertIn('href="/about"', note)
        self.assertIn("자동화 도구", note)
        self.assertNotIn("직접 테스트했습니다", note)
        self.assertIn('type="application/ld+json"', script)
        payload = json.loads(re.search(r">(.+)</script>", script).group(1))
        self.assertEqual(payload["@type"], "BlogPosting")
        self.assertEqual(payload["headline"], "주소모음 실제 이용 가이드")
        self.assertEqual(payload["mainEntityOfPage"]["@id"], url)
        self.assertEqual(payload["datePublished"], "2026-11-11")
        self.assertEqual(payload["author"]["@type"], "Organization")
        self.assertEqual(payload["publisher"]["name"], "링크위키")
        self.assertNotIn("Person", script)
        self.assertNotIn("dateModified", payload)

    def test_unknown_publication_date_does_not_invent_date(self):
        note, script = article_provenance(
            "업무별 링크모음", "https://linkwiki.info/blog/undated/", None)
        self.assertIn("발행: 링크위키", note)
        self.assertEqual(script, "")

    def test_untrusted_article_title_cannot_inject_structured_html(self):
        note, script = article_provenance(
            '</script><script>alert("XSS")</script>',
            "https://linkwiki.info/blog/unsafe/", "2026-11-11")
        self.assertEqual(script.count("</script>"), 1)
        self.assertNotIn("</script><script>", script)
        self.assertNotIn("<script>alert", script)
        self.assertNotIn("alert", note)

    def test_all_generated_guides_have_authorship_and_source_explanation(self):
        dist = ROOT / "dist" / "blog"
        if not dist.is_dir():
            self.skipTest("Build has not run")
        for file in sorted(dist.glob("*/index.html")):
            with self.subTest(page=file.parent.name):
                html = file.read_text(encoding="utf-8")
                self.assertEqual(html.count('class="blog-source-note"'), 1)
                self.assertIn('href="/about">자료 작성·확인 원칙</a>', html)
                if re.search(r"seo-20[0-9]{6}", file.parent.name):
                    self.assertIn('"@type":"BlogPosting"', html)
                    self.assertIn('"datePublished":', html)
                    self.assertNotIn('"@type":"Person"', html)

    def test_visible_and_structured_update_dates_match_the_sitemap(self):
        import xml.etree.ElementTree as ET

        dist = ROOT / "dist"
        if not (dist / "sitemap.xml").is_file():
            self.skipTest("Build first")
        updates = json.loads((ROOT / "seo/significant-page-updates.json").read_text())
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        dates = {
            row.findtext("s:loc", namespaces=ns): row.findtext("s:lastmod", namespaces=ns)
            for row in ET.parse(dist / "sitemap.xml").getroot()
        }
        for url, day in updates.items():
            if not url.startswith("/blog/"):
                continue
            with self.subTest(url=url):
                html = (dist / url.strip("/") / "index.html").read_text()
                scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html)
                posting = next(json.loads(script) for script in scripts if '"BlogPosting"' in script)
                self.assertLess(posting["datePublished"], day)
                self.assertEqual(posting["dateModified"], day)
                self.assertIn(f'수정 <time datetime="{day}">', html)
                self.assertEqual(dates["https://linkwiki.info" + url], day)

    def test_about_page_explains_automated_article_workflow_limits(self):
        about = (ROOT / "about.html").read_text(encoding="utf-8")
        self.assertIn("글 작성과 정보 확인 범위", about)
        self.assertIn("자동화 도구", about)
        self.assertIn("실시간 정확성", about)
        self.assertIn("직접 이용한 경험", about)


if __name__ == "__main__":
    unittest.main()
