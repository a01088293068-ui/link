import unittest
from seo.live_crawl_smoke import inspect

ORIGIN = "https://linkwiki.info"


def good_fetch(path):
    bodies = {
        "/": '<html><head><link rel="canonical" href="https://linkwiki.info/"></head><body><a href="/directory">전체 목록</a></body></html>',
        "/directory": '<html><head><link rel="canonical" href="https://linkwiki.info/directory"></head><body>목록</body></html>',
        "/categories/": '<html><head><link rel="canonical" href="https://linkwiki.info/categories/"></head><body>분야</body></html>',
        "/robots.txt": "User-agent: *\nAllow: /\nSitemap: https://linkwiki.info/sitemap.xml\nSitemap: https://linkwiki.info/sitemap-v2.xml\n",
        "/sitemap.xml": '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://linkwiki.info/</loc></url><url><loc>https://linkwiki.info/directory</loc></url></urlset>',
    }
    bodies["/sitemap-v2.xml"] = bodies["/sitemap.xml"]
    return 200, ORIGIN + path, bodies[path]


class DeploymentSmokeTests(unittest.TestCase):
    def test_mixed_unscoped_noindex_is_not_discarded_by_bot_suffix(self):
        from seo.live_crawl_smoke import google_noindex
        self.assertTrue(google_noindex(["noindex, Googlebot: nofollow"]))
        self.assertTrue(google_noindex(["OtherBot: nofollow, Googlebot: noindex"]))
        self.assertFalse(google_noindex(["OtherBot: noindex, Googlebot: follow"]))
        self.assertFalse(google_noindex(["googlebot-news: noindex"]))

    def test_mixed_header_flags_live_directory(self):
        def mixed(path):
            status, url, body = good_fetch(path)
            header = ["noindex, Googlebot: follow"] if path == "/directory" else []
            return status, url, body, header
        findings, _ = inspect(mixed)
        self.assertIn("/directory: X-Robots-Tag HTTP noindex directive found", findings)

    def test_x_robots_tag_blocks_directory_for_google(self):
        def blocked(path):
            status, url, body = good_fetch(path)
            values = ["Googlebot: noindex, nofollow"] if path == "/directory" else []
            return status, url, body, values
        findings, _ = inspect(blocked)
        self.assertIn("/directory: X-Robots-Tag HTTP noindex directive found", findings)

    def test_otherbot_only_header_does_not_block_google(self):
        def unrelated(path):
            status, url, body = good_fetch(path)
            return status, url, body, ["OtherBot: noindex"]
        findings, _ = inspect(unrelated)
        self.assertEqual(findings, [])

    def test_html_noindex_is_still_detected(self):
        def blocked(path):
            status, url, body = good_fetch(path)
            if path == "/":
                body = body.replace("<head>", '<head><meta name="robots" content="noindex,follow">')
            return status, url, body
        findings, _ = inspect(blocked)
        self.assertIn("/: HTML robots noindex directive found", findings)

    def test_valid_live_fixtures(self):
        problems, records = inspect(good_fetch)
        self.assertEqual(problems, [])
        self.assertEqual(len(records), 6)

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
                        "Sitemap: https://linkwiki.info/sitemap.xml\nSitemap: https://linkwiki.info/sitemap-v2.xml\n")
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
                        "Sitemap: https://linkwiki.info/sitemap.xml\nSitemap: https://linkwiki.info/sitemap-v2.xml\n")
            return status, url, body
        findings, _ = inspect(blocked)
        self.assertEqual(findings, [])

    def test_robots_sitemap_parsing_ignores_comments_and_accepts_spacing(self):
        def tagged(path):
            status, url, body = good_fetch(path)
            if path == "/robots.txt":
                body = ("User-agent: *\nAllow: /\n"
                        "Sitemap:https://linkwiki.info/sitemap.xml # valid\nSitemap: https://linkwiki.info/sitemap-v2.xml\n")
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


    def test_alternate_sitemap_drift_and_missing_directory_are_detected(self):
        def stale_alternate(path):
            status, url, body = good_fetch(path)
            if path == "/sitemap-v2.xml":
                body = body.replace("<url><loc>https://linkwiki.info/directory</loc></url>", "")
            return status, url, body

        findings, _ = inspect(stale_alternate)
        self.assertIn("sitemap.xml and sitemap-v2.xml: live XML contents differ", findings)
        self.assertIn("sitemap-v2.xml: /directory missing", findings)

    def test_sitemap_rejects_legacy_duplicate_and_foreign_urls(self):
        def bad_sitemap(path):
            status, url, body = good_fetch(path)
            if path == "/sitemap.xml":
                body = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        '<url><loc>https://linkwiki.info/</loc></url>'
                        '<url><loc>https://linkwiki.info/directory</loc></url>'
                        '<url><loc>https://linkwiki.info/directory</loc></url>'
                        '<url><loc>https://linkwiki.info/directory.html</loc></url>'
                        '<url><loc>https://other.example/page</loc></url>'
                        '</urlset>')
            return status, url, body

        findings, _ = inspect(bad_sitemap)
        self.assertIn("sitemap.xml: duplicate URL entries", findings)
        self.assertTrue(any("noncanonical URL" in x for x in findings))
        self.assertTrue(any("off-origin or invalid URL" in x for x in findings))


if __name__ == "__main__":
    unittest.main()
