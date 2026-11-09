from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from seo.live_release_check import (
    CATEGORY_PATHS, SITE, check_page, check_sitemap, parse_page, run,
)


def page(path, title, heading, more=""):
    return (f'<html lang="ko"><head><title>{title}</title>'
            f'<link rel="canonical" href="{SITE + path}"></head><body>'
            f'<h1>{heading}</h1>{more}</body></html>')


class LiveReleaseCheckTests(unittest.TestCase):
    def test_live_workflow_preserves_failure_diagnostics(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/live-crawl-check.yml").read_text(encoding="utf-8")
        self.assertIn("python3 seo/live_release_check.py --dist dist 2>&1 | tee -a seo/live-release-diagnosis.log", workflow)
        self.assertIn("name: linkwiki-live-release-diagnosis", workflow)
        self.assertIn("path: seo/live-release-diagnosis.log", workflow)
        self.assertIn("if: always()", workflow)

    def test_live_page_rejects_old_site_counts_even_when_h1_is_current(self):
        from seo.live_release_check import visible_site_counts
        for path in ("/", "/directory"):
            expected = page(
                path, "주소모음·링크모음·사이트모음", "188개 사이트 검색",
                "<p>현재 등록된 188개 사이트를 검색합니다.</p>"
                "<p>등록 사이트 188개</p>"
            )
            stale = expected.replace(
                "현재 등록된 188개 사이트", "현재 등록된 185개 사이트"
            ).replace("등록 사이트 188개</p>", "등록 사이트 183개</p>")
            self.assertEqual(visible_site_counts(expected), [188, 188, 188])
            self.assertEqual(visible_site_counts(stale), [183, 185, 188])
            self.assertTrue(any(
                "deployed visible site counts differ" in issue
                for issue in check_page(expected, stale, path)
            ))
            self.assertFalse(any(
                "deployed visible site counts differ" in issue
                for issue in check_page(expected, expected, path)
            ))

    def test_site_count_comparison_ignores_scripts_and_metadata(self):
        from seo.live_release_check import visible_site_counts
        markup = ('<html><head><meta content="185개 사이트"></head><body>'
                  '<script>const html = "183개 사이트";</script>'
                  '<h1>188개 사이트 검색</h1>'
                  '<p>등록 <strong>사이트</strong> 188개</p></body></html>')
        self.assertEqual(visible_site_counts(markup), [188, 188])

    def test_live_release_detects_stale_search_snippet_with_unchanged_title(self):
        path = "/categories/search"
        expected = page(path, "검색·포털·공공정보 사이트모음", "검색·포털 링크모음")
        expected = expected.replace(
            "</head>",
            '<meta name="description" content="정부24와 RISS 등 한국어 검색 안내"></head>')
        stale = expected.replace("정부24와 RISS", "이전 포털 목록")
        self.assertEqual(parse_page(expected).descriptions,
                         ["정부24와 RISS 등 한국어 검색 안내"])
        self.assertTrue(any("deployed meta description differs" in issue
                            for issue in check_page(expected, stale, path)))
        self.assertFalse(any("deployed meta description differs" in issue
                             for issue in check_page(expected, expected, path)))
        missing = expected.replace(
            '<meta name="description" content="정부24와 RISS 등 한국어 검색 안내">', "")
        self.assertTrue(any("deployed meta description differs" in issue
                            for issue in check_page(expected, missing, path)))

    def test_each_category_deployment_checks_distinct_editorial_copy(self):
        from seo.live_release_check import release_content_sections
        for path in CATEGORY_PATHS:
            with self.subTest(path=path):
                block = ('<section class="wrap seo-related-links seo-category-decision" '
                         'aria-label="이 분야의 목적별 선택 방법">'
                         '<h2>이 분야에서 사이트를 선택하는 방법</h2>'
                         '<ol><li><h3>목적별 안내</h3><p>이 분야의 정보 검토</p></li></ol>'
                         '</section>')
                expected = page(path, "분야별 사이트", "사이트 탐색", block)
                stale = expected.replace("이 분야의 정보 검토", "예전 정보")
                self.assertEqual(release_content_sections(expected, path), [block])
                self.assertTrue(any("directory examples differ" in issue
                                    for issue in check_page(expected, stale, path)))

    def test_category_sitemap_lastmod_mismatch_detected(self):
        from seo.live_release_check import check_core_sitemap_lastmod
        path = "/categories/ai"
        def sitemap(day):
            return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    f'<url><loc>{SITE + path}</loc><lastmod>{day}</lastmod></url></urlset>')
        errors = check_core_sitemap_lastmod(sitemap("2026-11-08"), sitemap("2026-11-07"))
        self.assertIn("deployed lastmod for /categories/ai differs", errors[0])

    def test_detects_outdated_site_cards_even_with_matching_title_and_h1(self):
        from seo.live_release_check import directory_cards
        card = ('<article class="v6-card"><small>AI 도구</small><h3>ChatGPT</h3>'
                '<p>글쓰기와 요약</p><span class="site-domain">chatgpt.com</span>'
                '<a href="https://chatgpt.com/">방문</a></article>')
        expected = page("/directory", "목록", "주소모음·링크모음·사이트모음", card)
        self.assertEqual(len(directory_cards(expected)), 1)
        for stale in (card.replace("글쓰기와 요약", "예전 설명"),
                      card.replace("chatgpt.com</span>", "old.example</span>"),
                      card.replace("https://chatgpt.com/", "https://other.example/"),
                      ""):
            live = expected.replace(card, stale)
            self.assertTrue(any("deployed site cards differ" in issue
                                for issue in check_page(expected, live, "/directory")))
        self.assertFalse(any("deployed site cards differ" in x
                             for x in check_page(expected, expected, "/directory")))

    def test_directory_card_compare_ignores_attribute_and_whitespace_formatting(self):
        from seo.live_release_check import directory_cards
        card = ('<article class="v6-card" data-extra="1"><h3>ChatGPT</h3>'
                '<small>AI 도구</small><p> 글쓰기 </p>'
                '<span class="site-domain">chatgpt.com</span>'
                '<a rel="nofollow" href="https://chatgpt.com/">방문</a></article>')
        other = card.replace('class="v6-card" data-extra="1"', 'data-extra="2" class="v6-card"')
        self.assertEqual(directory_cards(card), directory_cards(other))

    def test_sitemap_core_lastmod_comparison_catches_stale_deployment(self):
        from seo.live_release_check import check_core_sitemap_lastmod
        def sitemap(day):
            return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    '<url><loc>https://linkwiki.info/directory</loc>'
                    f'<lastmod>{day}</lastmod></url></urlset>')
        self.assertEqual(check_core_sitemap_lastmod(sitemap("2026-11-07"),
                                                     sitemap("2026-11-07")), [])
        problems = check_core_sitemap_lastmod(sitemap("2026-11-07"),
                                              sitemap("2026-10-29"))
        self.assertIn("sitemap.xml: deployed lastmod for /directory differs", problems[0])

    def test_directory_help_with_id_before_class_is_checked(self):
        from seo.live_release_check import release_content_sections
        help_html = ('<section id="site-list-guide" class="lw-safety-note seo-search-help" '
                     'aria-label="사이트모음 검색 및 확인 방법">'
                     '<h2>검색 안내</h2></section>')
        expected = page("/directory", "검색", "주소모음·링크모음·사이트모음", help_html)
        stale = expected.replace("검색 안내", "오래된 안내")
        self.assertEqual(release_content_sections(expected, "/directory"), [help_html])
        self.assertTrue(any("directory examples differ" in p
                            for p in check_page(expected, stale, "/directory")))

    def test_category_hub_detects_stale_registered_examples(self):
        from seo.live_release_check import release_content_sections
        links = ''.join(f'<a href="{link}">분야</a>' for link in CATEGORY_PATHS)
        expected = page("/categories/", "분야별", "분야별 사이트모음",
                        '<article class="v6-card"><p>등록 예시: ChatGPT</p></article>' + links)
        stale = expected.replace("ChatGPT", "오래된 목록")
        self.assertEqual(len(release_content_sections(expected, "/categories/")), 1)
        self.assertTrue(any("directory examples differ" in p
                            for p in check_page(expected, stale, "/categories/")))
        self.assertEqual(check_page(expected, expected, "/categories/"), [])

    def test_category_hub_missing_direct_category_link_is_detected(self):
        complete = page("/categories/", "분야별", "분야별", ''.join(
            f'<a href="{link}">보기</a>' for link in CATEGORY_PATHS))
        broken = complete.replace(f'<a href="{CATEGORY_PATHS[0]}">보기</a>', '')
        self.assertIn(f"/categories/: missing category link {CATEGORY_PATHS[0]}",
                      check_page(complete, broken, "/categories/"))

    def test_live_release_flags_missing_search_help_section(self):
        from seo.live_release_check import release_content_sections
        expected = page("/directory", "검색", "주소모음·링크모음·사이트모음 통합 검색",
                        '<section class="lw-safety-note seo-search-help" aria-label="사용법">'
                        '<h2>검색 사용 방법</h2></section>')
        stale = expected.replace("검색 사용 방법", "예전 안내")
        self.assertEqual(len(release_content_sections(expected, "/directory")), 1)
        self.assertTrue(any("directory examples differ" in problem
                            for problem in check_page(expected, stale, "/directory")))

    def test_detects_stale_deployed_site_examples_with_unchanged_title(self):
        from seo.live_release_check import release_content_sections
        home = page("/", "링크위키", "링크위키 주소모음", (
            '<form action="/directory" class="lw-search" method="get" role="search"></form>'
            '<section aria-label="주소모음 링크모음 사이트모음 이용 안내">'
            '<a href="/directory">전체</a><a href="/categories/">분야별</a></section>'
            '<section class="wrap seo-directory-examples" aria-label="실제 등록 사이트 분야별 예시">'
            '<article><h3>AI 도구</h3><p>등록 도메인: chatgpt.com</p></article></section>'))
        stale = home.replace("chatgpt.com", "outdated.example")
        self.assertEqual(len(release_content_sections(home, "/")), 1)
        self.assertTrue(any("directory examples differ" in error
                            for error in check_page(home, stale, "/")))
        self.assertEqual(check_page(home, home, "/"), [])

    def test_detects_stale_directory_category_overview(self):
        from seo.live_release_check import release_content_sections
        links = ''.join(f'<a href="{url}">분야</a>' for url in CATEGORY_PATHS)
        directory = page("/directory", "검색", "주소모음·링크모음·사이트모음 통합 검색",
                         '<input id="v6-query"><div id="v6-results"></div>'
                         '<script id="directory-category-schema"></script>' + links +
                         '<section class="seo-directory-category"><h3>AI 도구</h3>'
                         '<p>등록 사이트 4개</p></section>')
        stale = directory.replace("등록 사이트 4개", "등록 사이트 3개")
        self.assertEqual(len(release_content_sections(directory, "/directory")), 1)
        self.assertTrue(any("directory examples differ" in error
                            for error in check_page(directory, stale, "/directory")))
        self.assertEqual(check_page(directory, directory, "/directory"), [])

    def test_accepts_correct_live_home_and_directory(self):
        home = page("/", "링크위키", "링크위키 주소모음", (
            '<form action="/directory" class="lw-search" method="get" role="search"></form>'
            '<section aria-label="주소모음 링크모음 사이트모음 이용 안내">'
            '<a href="/directory">전체</a><a href="/categories/">분야별</a></section>'))
        directory = page("/directory", "검색", "주소모음·링크모음·사이트모음 통합 검색",
                         '<input id="v6-query"><div id="v6-results"></div>'
                         '<script id="directory-category-schema"></script>' +
                         ''.join(f'<a href="{url}">분야</a>' for url in CATEGORY_PATHS))
        self.assertEqual(check_page(home, home, "/"), [])
        self.assertEqual(check_page(directory, directory, "/directory"), [])
        parsed = parse_page(directory)
        self.assertEqual(parsed.canonicals, [SITE + "/directory"])

    def test_finds_live_drift_even_when_http_200(self):
        home = page("/", "링크위키", "키워드", (
            '<form action="/directory" class="lw-search" method="get" role="search"></form>'
            '<section aria-label="주소모음 링크모음 사이트모음 이용 안내">'
            '<a href="/directory">목록</a><a href="/categories/">분야</a></section>'))
        stale = page("/", "예전 제목", "키워드", '<a href="/directory">목록</a>')
        problems = check_page(home, stale, "/")
        self.assertTrue(any("title" in item for item in problems))
        self.assertTrue(any("intent section" in item for item in problems))
        self.assertTrue(any("canonical /directory" in item for item in problems))
        self.assertTrue(any("category hub" in item for item in problems))

    def test_rejects_robots_noindex_duplicate_canonical_and_missing_categories(self):
        expected = page("/directory", "검색", "주소모음·링크모음·사이트모음 통합 검색")
        bad = (expected.replace("</head>",
                                '<meta name="robots" content="index, noindex">'
                                f'<link href="{SITE}/directory" rel="canonical"></head>')
               .replace("<body>", '<body><input id="v6-query">'))
        problems = check_page(expected, bad, "/directory")
        self.assertTrue(any("noindex" in x for x in problems))
        self.assertTrue(any("canonical" in x for x in problems))
        self.assertTrue(any("structured-data" in x for x in problems))
        self.assertTrue(any("category link" in x for x in problems))

    def test_sitemap_requires_real_hubs_and_all_eight_categories(self):
        locs = [SITE + "/", SITE + "/directory", SITE + "/categories/"]
        locs.extend(SITE + x for x in CATEGORY_PATHS)
        good = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
            f"<url><loc>{x}</loc></url>" for x in locs) + "</urlset>"
        self.assertEqual(check_sitemap(good), [])
        self.assertTrue(any("categories/video" in x for x in
                            check_sitemap(good.replace(f"<url><loc>{SITE}/categories/video</loc></url>", ""))))
        self.assertTrue(any("invalid" in x for x in check_sitemap("<invalid")))

    def test_run_uses_injected_public_fetch_and_flags_missing_live_script(self):
        with TemporaryDirectory() as temp:
            dist = Path(temp)
            home = page("/", "홈", "주소모음", (
                '<form action="/directory" class="lw-search" method="get" role="search"></form>'
            '<section aria-label="주소모음 링크모음 사이트모음 이용 안내">'
                '<a href="/directory">목록</a><a href="/categories/">분야</a></section>'))
            directory = page("/directory", "목록", "주소모음 링크모음 사이트모음",
                             '<input id="v6-query"><div id="v6-results"></div>'
                             '<script id="directory-category-schema"></script>' +
                             ''.join(f'<a href="{x}">바로가기</a>' for x in CATEGORY_PATHS))
            (dist / "index.html").write_text(home, encoding="utf-8")
            (dist / "directory.html").write_text(directory, encoding="utf-8")
            hub = page("/categories/", "분야별", "분야별 사이트모음",
                       ''.join(f'<a href="{link}">보기</a>' for link in CATEGORY_PATHS))
            (dist / "categories").mkdir()
            (dist / "categories/index.html").write_text(hub, encoding="utf-8")
            for category_path in CATEGORY_PATHS:
                slug = category_path.rsplit("/", 1)[-1]
                category_html = page(category_path, slug, "카테고리",
                    '<section class="wrap seo-related-links seo-category-decision"><h2>목적별 선택</h2></section>')
                (dist / "categories" / (slug + ".html")).write_text(
                    category_html, encoding="utf-8")
            sitemap = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
                f"<url><loc>{x}</loc></url>"
                for x in [SITE + "/", SITE + "/directory", SITE + "/categories/"] +
                         [SITE + x for x in CATEGORY_PATHS]) + "</urlset>"
            pages = {"/": home, "/directory": directory, "/categories/": hub,
                     "/sitemap.xml": sitemap, "/assets/directory.js": "old",
                     "/assets/directory-search.js": "old"}
            for category_path in CATEGORY_PATHS:
                slug = category_path.rsplit("/", 1)[-1]
                pages[category_path] = page(category_path, slug, "카테고리",
                    '<section class="wrap seo-related-links seo-category-decision"><h2>목적별 선택</h2></section>')
            self.assertTrue(any("multi-term search" in x for x in
                                run(dist, fetch=lambda path: pages[path])))
            pages["/assets/directory.js"] = "window.LinkWikiSearch.sortResults"
            pages["/assets/directory-search.js"] = "terms.every(term => haystack.includes(term)) function sortResults("
            self.assertEqual(run(dist, fetch=lambda path: pages[path]), [])


if __name__ == "__main__":
    unittest.main()
