"""Pure, offline sitemap delivery diagnostics. No live network calls."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "seo/sitemap_http_diagnostic.py"
spec = importlib.util.spec_from_file_location("sitemap_http_diagnostic", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SITE = "https://linkwiki.info"
XML = (b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
       b'<url><loc>https://linkwiki.info/</loc></url>'
       b'<url><loc>https://linkwiki.info/directory</loc></url></urlset>')


def result(url, body=XML, content_type="application/xml"):
    return {"status": 200, "url": url, "body": body, "content_type": content_type}


class SitemapHttpDiagnosticTests(unittest.TestCase):
    def test_valid_sitemap(self):
        self.assertEqual(len(module.parse_sitemap(result(SITE + "/sitemap.xml"))), 2)

    def test_reject_html_document(self):
        with self.assertRaisesRegex(ValueError, "XML parse error"):
            module.parse_sitemap(result(SITE + "/sitemap.xml", b'<html><body>ok</body></html>'))

    def test_reject_redirecting_html_loc(self):
        altered = XML.replace(b"/directory</loc>", b"/directory.html</loc>")
        with self.assertRaisesRegex(ValueError, "redirect"):
            module.parse_sitemap(result(SITE + "/sitemap.xml", altered))

    def test_reject_host_swap(self):
        with self.assertRaisesRegex(ValueError, "unexpected host"):
            module.parse_sitemap(result("https://untrusted.invalid/sitemap.xml"))

    def test_reject_duplicates(self):
        body = XML.replace(b"</urlset>", b"<url><loc>https://linkwiki.info/</loc></url></urlset>")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.parse_sitemap(result(SITE + "/sitemap.xml", body))

    def test_matching_robots_and_sitemap_pass(self):
        def fake(url):
            if url.endswith("robots.txt"):
                return result(url, b"User-agent: *\nAllow: /\nSitemap: https://linkwiki.info/sitemap.xml\nSitemap: https://linkwiki.info/sitemap-v2.xml\n", "text/plain")
            return result(url)
        markdown, errors = module.check(fake)
        self.assertEqual(errors, [])
        self.assertIn("internally consistent", markdown)

    def test_missing_robots_directive_detected(self):
        def fake(url):
            if url.endswith("robots.txt"):
                return result(url, b"Sitemap: https://linkwiki.info/sitemap.xml", "text/plain")
            return result(url)
        _, errors = module.check(fake)
        self.assertTrue(any("sitemap-v2.xml" in item for item in errors))

    def test_bad_mime_type_detected(self):
        def fake(url):
            if url.endswith("robots.txt"):
                return result(url, b"Sitemap: https://linkwiki.info/sitemap.xml\nSitemap: https://linkwiki.info/sitemap-v2.xml", "text/plain")
            return result(url, content_type="text/html")
        _, errors = module.check(fake)
        self.assertTrue(any("Content-Type" in item for item in errors))

    def test_mismatched_url_sets_detected(self):
        extra = XML.replace(b"</urlset>", b"<url><loc>https://linkwiki.info/about</loc></url></urlset>")
        def fake(url):
            if url.endswith("robots.txt"):
                return result(url, b"Sitemap: https://linkwiki.info/sitemap.xml\nSitemap: https://linkwiki.info/sitemap-v2.xml", "text/plain")
            return result(url, XML if url.endswith("/sitemap.xml") else extra)
        _, errors = module.check(fake)
        self.assertTrue(any("URL sets differ" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
