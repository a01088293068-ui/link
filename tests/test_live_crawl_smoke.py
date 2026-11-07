import unittest
from seo.live_crawl_smoke import inspect

ORIGIN = "https://linkwiki.info"


def good_fetch(path):
    bodies = {
        "/": '<html><head><link rel="canonical" href="https://linkwiki.info/"></head><body><a href="/directory">전체 목록</a></body></html>',
        "/directory": '<html><head><link rel="canonical" href="https://linkwiki.info/directory"></head><body>목록</body></html>',
        "/categories/": '<html><head><link rel="canonical" href="https://linkwiki.info/categories/"></head><body>분야</body></html>',
        "/robots.txt": "User-agent: *\nAllow: /\nSitemap: https://linkwiki.info/sitemap.xml\n",
        "/sitemap.xml": '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://linkwiki.info/</loc></url><url><loc>https://linkwiki.info/directory</loc></url></urlset>',
    }
    return 200, ORIGIN + path, bodies[path]


class DeploymentSmokeTests(unittest.TestCase):
    def test_valid_live_fixtures(self):
        problems, records = inspect(good_fetch)
        self.assertEqual(problems, [])
        self.assertEqual(len(records), 5)

    def test_missing_canonical_and_directory_link(self):
        def broken(path):
            status, url, body = good_fetch(path)
            if path == "/":
                body = '<html><head><link rel="canonical" href="https://linkwiki.info/index.html"></head><body></body></html>'
            return status, url, body
        problems, _ = inspect(broken)
        self.assertTrue(any("canonical" in issue for issue in problems))
        self.assertTrue(any("crawlable link" in issue for issue in problems))

    def test_googlebot_block_is_detected_on_directory_only(self):
        def blocked(path):
            status, url, body = good_fetch(path)
            if path == "/robots.txt":
                body = ("User-agent: Googlebot\nDisallow: /directory\n\n"
                        "User-agent: *\nAllow: /\n"
                        "Sitemap: https://linkwiki.info/sitemap.xml\n")
            return status, url, body
        findings, _ = inspect(blocked)
        self.assertIn("robots.txt: Googlebot disallowed /directory", findings)
        self.assertNotIn("robots.txt: Googlebot disallowed /", findings)

    def test_unrelated_bot_disallow_is_not_global_google_block(self):
        def blocked(path):
            status, url, body = good_fetch(path)
            if path == "/robots.txt":
                body = ("User-agent: OtherBot\nDisallow: /\n\n"
                        "User-agent: *\nAllow: /\n"
                        "Sitemap: https://linkwiki.info/sitemap.xml\n")
            return status, url, body
        findings, _ = inspect(blocked)
        self.assertEqual(findings, [])

    def test_robots_sitemap_parsing_ignores_comments_and_accepts_spacing(self):
        def tagged(path):
            status, url, body = good_fetch(path)
            if path == "/robots.txt":
                body = ("User-agent: *\nAllow: /\n"
                        "Sitemap:https://linkwiki.info/sitemap.xml # valid\n")
            return status, url, body
        findings, _ = inspect(tagged)
        self.assertEqual(findings, [])

    def test_fetch_failure_not_confused_with_unindexed(self):
        def broken(path):
            if path == "/directory":
                raise TimeoutError("network issue")
            return good_fetch(path)
        problems, records = inspect(broken)
        self.assertTrue(any("TimeoutError" in issue for issue in problems))
        self.assertFalse(any("not indexed" in issue for issue in problems))
        self.assertEqual(records[1][1], "ERROR")


if __name__ == "__main__":
    unittest.main()
