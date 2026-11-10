import unittest
from email.message import Message
from seo.check_release_drift import BASE, check

SOURCE = "<title>주소모음 링크모음 사이트모음</title><h1>주소모음 링크모음 사이트모음</h1>"
HOME = f'<title>주소모음 링크모음 사이트모음</title><link rel="canonical" href="{BASE}/"><h1>주소모음 링크모음 사이트모음</h1>'
DIRECTORY = f'<link rel="canonical" href="{BASE}/directory">'
ROBOTS = f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n"
SITEMAP = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}/</loc></url><url><loc>{BASE}/directory</loc></url></urlset>'

def fixture(path):
    return 200, BASE + path, {"/": HOME, "/directory": DIRECTORY, "/sitemap.xml": SITEMAP, "/robots.txt": ROBOTS}[path], Message()

class ReleaseDriftTests(unittest.TestCase):
    def test_healthy_release(self):
        problems, details = check(SOURCE, fixture)
        self.assertEqual(problems, [])
        self.assertEqual(len(details), 4)

    def test_stale_title_and_h1(self):
        def stale(path):
            status, url, body, headers = fixture(path)
            if path == "/": body = body.replace("주소모음 링크모음 사이트모음", "오래된 홈페이지")
            return status, url, body, headers
        problems, _ = check(SOURCE, stale)
        self.assertTrue(any("differs" in p for p in problems))
        self.assertTrue(any("missing 주소모음" in p for p in problems))

    def test_noindex_and_missing_sitemap(self):
        def broken(path):
            status, url, body, headers = fixture(path)
            if path == "/directory": headers["X-Robots-Tag"] = "noindex"
            if path == "/sitemap.xml": body = body.replace(f"<url><loc>{BASE}/directory</loc></url>", "")
            return status, url, body, headers
        problems, _ = check(SOURCE, broken)
        self.assertTrue(any("HTTP noindex" in p for p in problems))
        self.assertTrue(any("sitemap missing /directory" in p for p in problems))

    def test_robots_missing_sitemap_is_detected(self):
        def broken(path):
            status, url, body, headers = fixture(path)
            if path == "/robots.txt":
                body = "User-agent: *\nAllow: /\n"
            return status, url, body, headers
        problems, _ = check(SOURCE, broken)
        self.assertIn("/robots.txt: canonical sitemap reference missing", problems)

    def test_robots_googlebot_disallow_is_detected(self):
        def broken(path):
            status, url, body, headers = fixture(path)
            if path == "/robots.txt":
                body = (f"User-agent: Googlebot\nDisallow: /\n\n"
                        f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
            return status, url, body, headers
        problems, _ = check(SOURCE, broken)
        self.assertTrue(any("potential Googlebot block" in p for p in problems))

    def test_published_related_link_matches_build(self):
        from seo.check_release_drift import related_targets
        path = "/blog/sample-guide/"
        guide = (f'<link rel="canonical" href="{BASE}{path}">'
                 '<h1>커뮤니티 가이드</h1>'
                 '<section class="blog-related" aria-label="관련 사이트 이용 가이드">'
                 '<a href="/blog/other-guide/">다른 가이드</a></section>')
        self.assertEqual(related_targets(guide), {"/blog/other-guide/"})
        def load(url):
            if url == path:
                return 200, BASE + path, guide, Message()
            return fixture(url)
        problems, observations = check(SOURCE, load, article_sources={path: guide})
        self.assertEqual(problems, [])
        self.assertTrue(any("1 related links" in line for line in observations))

    def test_missing_live_related_link_is_detected(self):
        path = "/blog/sample-guide/"
        guide = (f'<link rel="canonical" href="{BASE}{path}">'
                 '<h1>커뮤니티 가이드</h1>'
                 '<section class="blog-related"><a href="/blog/other-guide/">다른 가이드</a></section>')
        def load(url):
            if url == path:
                return 200, BASE + path, guide.replace(
                    '<a href="/blog/other-guide/">다른 가이드</a>', ''), Message()
            return fixture(url)
        problems, _ = check(SOURCE, load, article_sources={path: guide})
        self.assertTrue(any("missing deployed related links" in p for p in problems))

    def test_article_noindex_is_detected(self):
        path = "/blog/sample-guide/"
        guide = (f'<link rel="canonical" href="{BASE}{path}">'
                 '<h1>커뮤니티 가이드</h1>'
                 '<section class="blog-related"><a href="/blog/other-guide/">다른 가이드</a></section>')
        def load(url):
            if url == path:
                return 200, BASE + path, '<meta name="robots" content="noindex">' + guide, Message()
            return fixture(url)
        problems, _ = check(SOURCE, load, article_sources={path: guide})
        self.assertTrue(any("article HTML noindex" in p for p in problems))

    def test_failed_fetch_is_not_claimed_as_unindexed(self):
        def error(path):
            if path == "/": raise TimeoutError("network")
            return fixture(path)
        problems, _ = check(SOURCE, error)
        self.assertTrue(any("fetch error" in p for p in problems))
        self.assertFalse(any("not indexed" in p for p in problems))

if __name__ == "__main__":
    unittest.main()
