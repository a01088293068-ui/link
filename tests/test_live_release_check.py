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
    def test_accepts_correct_live_home_and_directory(self):
        home = page("/", "링크위키", "링크위키 주소모음", (
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
            '<section aria-label="주소모음 링크모음 사이트모음 이용 안내">'
            '<a href="/directory">목록</a><a href="/categories/">분야</a></section>'))
        stale = page("/", "예전 제목", "키워드", '<a href="/directory">목록</a>')
        problems = check_page(home, stale, "/")
        self.assertTrue(any("title" in item for item in problems))
        self.assertTrue(any("intent section" in item for item in problems))
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
                '<section aria-label="주소모음 링크모음 사이트모음 이용 안내">'
                '<a href="/directory">목록</a><a href="/categories/">분야</a></section>'))
            directory = page("/directory", "목록", "주소모음 링크모음 사이트모음",
                             '<input id="v6-query"><div id="v6-results"></div>'
                             '<script id="directory-category-schema"></script>' +
                             ''.join(f'<a href="{x}">바로가기</a>' for x in CATEGORY_PATHS))
            (dist / "index.html").write_text(home, encoding="utf-8")
            (dist / "directory.html").write_text(directory, encoding="utf-8")
            sitemap = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
                f"<url><loc>{x}</loc></url>"
                for x in [SITE + "/", SITE + "/directory", SITE + "/categories/"] +
                         [SITE + x for x in CATEGORY_PATHS]) + "</urlset>"
            pages = {"/": home, "/directory": directory,
                     "/sitemap.xml": sitemap, "/assets/directory.js": "old"}
            self.assertTrue(any("core query behavior" in x for x in
                                run(dist, fetch=lambda path: pages[path])))
            pages["/assets/directory.js"] = "const lookup=coreIntent?'':q"
            self.assertEqual(run(dist, fetch=lambda path: pages[path]), [])


if __name__ == "__main__":
    unittest.main()
