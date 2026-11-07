from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from seo.site_audit import SITE, audit_site, page_file, has_noindex_meta, internal_inbound_links


class SiteAuditTests(unittest.TestCase):
    def test_visible_directory_card_copy_matches_registered_metadata(self):
        from seo.site_audit import card_copy_errors
        record = {"name": "테스트 <도구>", "category": "AI 도구",
                  "description": "검색 & 글쓰기", "url": "https://tools.example/"}
        body = ('<small>AI 도구</small><h3>테스트 &lt;도구&gt;</h3>'
                '<p>검색 &amp; 글쓰기</p>'
                '<span class="site-domain">tools.example</span>'
                '<a href="https://tools.example/">방문</a>')
        self.assertEqual(card_copy_errors([body], [record], "h3", "directory"), [])
        stale = body.replace("검색 &amp; 글쓰기", "오래된 설명")
        self.assertIn("directory card #1 description differs from JSON",
                      card_copy_errors([stale], [record], "h3", "directory"))
        stale = body.replace("tools.example</span>", "other.example</span>")
        self.assertIn("directory card #1 domain differs from JSON",
                      card_copy_errors([stale], [record], "h3", "directory"))
        stale = body.replace("테스트 &lt;도구&gt;", "테스트 다른 이름")
        self.assertIn("directory card #1 name differs from JSON",
                      card_copy_errors([stale], [record], "h3", "directory"))

    def test_category_card_copy_is_checked_independently(self):
        from seo.site_audit import card_copy_errors
        record = {"name": "예시", "category": "검색·포털",
                  "description": "포털 설명", "url": "https://example.org/"}
        body = ('<strong>예시</strong><small>검색·포털</small><p>포털 설명</p>'
                '<span class="site-domain">example.org</span>'
                '<a href="https://example.org/">방문</a>')
        self.assertEqual(card_copy_errors([body], [record], "strong", "search"), [])
        stale = body.replace("<small>검색·포털</small>", "<small>다른 분야</small>")
        self.assertIn("search card #1 category differs from JSON",
                      card_copy_errors([stale], [record], "strong", "search"))

    def test_homepage_examples_use_real_records_and_escaped_text(self):
        from build import homepage_directory_examples
        categories = (("AI 도구", "ai", "AI 도구 사이트모음", "비교"),)
        records = [{"category": "AI 도구", "name": "테스트 <AI>",
                    "description": "글쓰기 & 검색 도구",
                    "url": "https://example.org/tools?ref=directory"}]
        rendered = homepage_directory_examples(records, categories)
        self.assertIn("테스트 &lt;AI&gt;", rendered)
        self.assertIn("글쓰기 &amp; 검색 도구", rendered)
        self.assertIn("등록 도메인: example.org", rendered)
        self.assertNotIn("ref=directory", rendered)
        self.assertIn('href="/categories/ai"', rendered)
        self.assertIn("인기 순위나 추천 등급이 아니며", rendered)
        self.assertNotIn("테스트 <AI>", rendered)
        with self.assertRaises(RuntimeError):
            homepage_directory_examples([], categories)
        with self.assertRaises(RuntimeError):
            homepage_directory_examples(records, (("스포츠", "sports", "스포츠", "비교"),))
        with self.assertRaises(RuntimeError):
            homepage_directory_examples(
                [{"category": "AI 도구", "name": "test", "description": "test",
                  "url": "http://example.org/"}], categories)

    def test_directory_seo_count_updates_but_category_count_stays_intact(self):
        from build import sync_directory_count
        sample = ('<title>97개 사이트</title>'
                  '<meta name="description" content="97개 사이트의 목록">'
                  '<meta property="og:title" content="97개 사이트">'
                  '<meta property="og:description" content="97개 사이트의 목록">'
                  '<p>97개 등록 사이트의 설명</p>'
                  '<p>등록 사이트 97개</p><p>8개 분야</p>')
        fixed = sync_directory_count(sample, 112)
        self.assertEqual(fixed.count("112개"), 6)
        self.assertNotIn("97개", fixed)
        self.assertIn("8개 분야", fixed)
        with self.assertRaises(RuntimeError):
            sync_directory_count("<html>97개 사이트</html>", 112)

    def test_homepage_directory_count_is_checked_against_json(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(
                json.dumps([{"name": "Example", "category": "검색·포털",
                             "description": "Example", "url": "https://example.org/"}]),
                encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            home = root / "index.html"
            home.write_text("<html><body>97개 등록 사이트, 97개 등록 항목</body></html>", encoding="utf-8")
            errors = audit_site(root)
            self.assertTrue(any("homepage directory count mismatch: 등록 사이트" in x for x in errors))
            self.assertTrue(any("homepage directory count mismatch: 등록 항목" in x for x in errors))
            home.write_text("<html><body>1개 등록 사이트, 1개 등록 항목</body></html>", encoding="utf-8")
            errors = audit_site(root)
            self.assertFalse(any("homepage directory count" in x for x in errors), errors)

    def test_robots_noindex_is_detected_with_either_attribute_order(self):
        samples = [
            '<meta name="robots" content="noindex,follow">',
            '<meta content="follow, noindex" name="robots">',
            "<META CONTENT='none' NAME='googlebot'>",
        ]
        for html in samples:
            with self.subTest(html=html):
                self.assertTrue(has_noindex_meta(html))
        self.assertFalse(has_noindex_meta('<meta name="robots" content="index,follow">'))
        self.assertFalse(has_noindex_meta('<meta name="description" content="noindex notice">'))
        self.assertFalse(has_noindex_meta('<meta name="robots" content="noindexing">'))

    def test_audit_catches_index_blocker_in_sitemap_page(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "blog").mkdir()
            (root / "assets").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(
                json.dumps([{"name": "Test", "category": "검색·포털", "description": "Test",
                             "url": "https://example.org/"}]), encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url>'
                       f'<url><loc>{SITE}/test</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "test.html").write_text(
                f'<html><head><title>Example</title><link rel="canonical" href="{SITE}/test">'
                '<meta content="noindex,follow" name="robots"></head><body></body></html>',
                encoding="utf-8")
            issues = audit_site(root)
            self.assertTrue(any("indexable page blocked by robots noindex: test.html" in issue
                                for issue in issues), issues)

    def test_audit_rejects_missing_empty_or_duplicate_meta_descriptions(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(
                json.dumps([{"name": "Example", "category": "검색·포털",
                             "description": "Example", "url": "https://example.org/"}]),
                encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url>'
                       f'<url><loc>{SITE}/test</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            page = root / "test.html"
            prefix = (f'<html><head><title>Example</title>'
                      f'<link rel="canonical" href="{SITE}/test">')
            for desc in (
                "",
                '<meta name="description" content="   ">',
                '<meta name="description" content="One">'
                '<meta content="Two" name="description">',
            ):
                with self.subTest(description=desc):
                    page.write_text(prefix + desc + '</head><body></body></html>',
                                    encoding="utf-8")
                    errors = audit_site(root)
                    self.assertTrue(any('missing, empty or duplicate meta description: test.html'
                                        in item for item in errors), errors)
            page.write_text(prefix + '<meta content="Actual helpful description" name="description">'
                            '</head><body></body></html>', encoding="utf-8")
            self.assertFalse(any('meta description: test.html' in item
                                 for item in audit_site(root)))

    def test_audit_rejects_global_robots_block_and_duplicate_sitemap_urls(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(
                json.dumps([{"name": "Example", "category": "검색·포털",
                             "description": "Example", "url": "https://example.org/"}]),
                encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url>'
                       f'<url><loc>{SITE}/blog/</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "robots.txt").write_text(
                'User-agent: *\nDisallow: /\nSitemap: https://linkwiki.info/sitemap.xml\n',
                encoding="utf-8")
            errors = audit_site(root)
            self.assertIn("duplicate URL in sitemap", errors)
            self.assertIn("robots.txt globally disallows crawling", errors)
            (root / "robots.txt").write_text(
                'User-agent: *\nDisallow: /admin/\n'
                'Sitemap: https://linkwiki.info/sitemap.xml\n', encoding="utf-8")
            errors = audit_site(root)
            self.assertNotIn("robots.txt globally disallows crawling", errors)
            self.assertNotIn("robots.txt missing canonical sitemap URL", errors)
            (root / "robots.txt").write_text('User-agent: *\nAllow: /\n', encoding="utf-8")
            self.assertIn("robots.txt missing canonical sitemap URL", audit_site(root))

    def test_internal_inbound_links_detect_real_navigation_not_self_links(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "blog/post").mkdir(parents=True)
            (root / "index.html").write_text(
                '<html><body><a href="/directory.html">Directory</a>'
                '<a href="/blog/post/">Read guide</a></body></html>', encoding="utf-8")
            (root / "directory.html").write_text(
                '<html><body><a href="/directory">Self</a>'
                '<a href="https://other.example/directory">Off-site</a></body></html>',
                encoding="utf-8")
            (root / "blog/post/index.html").write_text(
                '<html><body><a href="/blog/post/">Self</a></body></html>',
                encoding="utf-8")
            links = internal_inbound_links(root)
            self.assertEqual(links["/directory"], {"/"})
            self.assertEqual(links["/blog/post/"], {"/"})

    def test_audit_catches_orphan_directory_and_published_article(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "blog/post").mkdir(parents=True)
            (root / "assets").mkdir()
            (root / "assets/verified-directory.json").write_text(
                json.dumps([{"name": "Example", "category": "검색·포털",
                             "description": "Example", "url": "https://example.org/"}]),
                encoding="utf-8")
            (root / "directory.html").write_text('<html><body>No inbound</body></html>', encoding="utf-8")
            (root / "blog/post/index.html").write_text(
                f'<html><head><link href="{SITE}/blog/post/" rel="canonical">'
                '<title>Post</title></head><body>No inbound</body></html>', encoding="utf-8")
            (root / "blog/index.html").write_text('<html><body>Index</body></html>', encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url>'
                       f'<url><loc>{SITE}/blog/post/</loc></url>'
                       f'<url><loc>{SITE}/directory</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "robots.txt").write_text(
                'User-agent: *\\nAllow: /\\nSitemap: https://linkwiki.info/sitemap.xml\\n',
                encoding="utf-8")
            issues = audit_site(root)
            self.assertIn('orphan core directory page: /directory', issues)
            self.assertIn('orphan published article: blog/post/', issues)

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

    def test_audit_catches_directory_cards_out_of_sync(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(json.dumps([
                {"name": "예시", "category": "검색", "description": "예시", "url": "https://example.com/"}
            ], ensure_ascii=False), encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "directory.html").write_text(
                '<article class="v6-card"><a href="https://wrong.example/">방문</a></article>',
                encoding="utf-8")
            self.assertTrue(any("directory card URL" in item for item in audit_site(root)))

    def test_audit_catches_category_cards_out_of_sync(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "assets").mkdir()
            (root / "blog").mkdir()
            (root / "categories").mkdir()
            (root / "blog/index.html").write_text("index", encoding="utf-8")
            (root / "assets/verified-directory.json").write_text(json.dumps([
                {"name": "예시", "category": "AI 도구", "description": "예시", "url": "https://example.com/"}
            ], ensure_ascii=False), encoding="utf-8")
            sitemap = (f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                       f'<url><loc>{SITE}/blog/</loc></url></urlset>')
            (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
            (root / "sitemap-v2.xml").write_text(sitemap, encoding="utf-8")
            (root / "categories/ai.html").write_text(
                '<article class="item"><a href="https://wrong.example/">방문</a></article>',
                encoding="utf-8")
            self.assertTrue(any("category card URLs differ" in item for item in audit_site(root)))

    def test_existing_generated_site_is_consistent(self):
        root = Path(__file__).resolve().parents[1] / "dist"
        if root.is_dir():
            self.assertEqual(audit_site(root), [])


if __name__ == "__main__":
    unittest.main()
