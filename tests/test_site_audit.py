from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from seo.site_audit import SITE, audit_site, page_file


class SiteAuditTests(unittest.TestCase):
    def test_site_paths_do_not_escape_dist(self):
        root = Path("/tmp/linkwiki-site-fixture")
        self.assertIsNone(page_file(root, "/../../secret"))
        self.assertIsNone(page_file(root, "/%2e%2e/secret"))
        self.assertEqual(page_file(root, "/blog/entry/"), root / "blog/entry/index.html")

    def test_audit_finds_missing_sitemap_entry_and_broken_link(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "blog/entry").mkdir(parents=True)
            (root / "assets").mkdir()
            (root / "assets/verified-directory.json").write_text(json.dumps([
                {"name": "예시", "category": "검색", "description": "예시 설명", "url": "https://example.com/"}
            ], ensure_ascii=False), encoding="utf-8")
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            sitemap = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE}/blog/</loc></url></urlset>'
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "blog/entry/index.html").write_text(
                f'<link rel="canonical" href="{SITE}/blog/entry/">'
                '<div class="blog-content"><a href="/blog/missing/">관련 글</a></div>',
                encoding="utf-8")
            problems = audit_site(root)
            self.assertTrue(any("absent from sitemap" in item for item in problems))
            self.assertTrue(any("broken internal article link" in item for item in problems))

    def test_audit_rejects_unvalidated_directory_url_format(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            sitemap = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE}/blog/</loc></url></urlset>'
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(json.dumps([
                {"name": "테스트", "category": "기타", "description": "테스트", "url": "javascript:alert(1)"}
            ], ensure_ascii=False), encoding="utf-8")
            self.assertTrue(any("invalid directory URL" in item for item in audit_site(root)))

    def test_audit_catches_broken_json_ld_and_breadcrumb(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(json.dumps([
                {"name": "예시", "category": "검색", "description": "예시", "url": "https://example.com/"}
            ], ensure_ascii=False), encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url>'
                       f'<url><loc>{SITE}/test</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "test.html").write_text(
                f'<html><head><title>검증</title><link rel="canonical" href="{SITE}/test">'
                '<script type="application/ld+json">{"@type":"BreadcrumbList",'
                '"itemListElement":[{"position":1,"item":"https://linkwiki.info/"},'
                '{"position":2,"item":"https://linkwiki.info/wrong"}]}</script>'
                '</head><body></body></html>', encoding="utf-8")
            self.assertTrue(any("breadcrumb URL mismatch" in item for item in audit_site(root)))
            (root / "test.html").write_text(
                f'<html><head><title>검증</title><link rel="canonical" href="{SITE}/test">'
                '<script type="application/ld+json">{broken}</script>'
                '</head></html>', encoding="utf-8")
            self.assertTrue(any("invalid JSON-LD" in item for item in audit_site(root)))

    def test_existing_generated_site_is_consistent(self):
        root = Path(__file__).resolve().parents[1] / "dist"
        if root.is_dir():
            self.assertEqual(audit_site(root), [])


if __name__ == "__main__":
    unittest.main()
