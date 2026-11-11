"""Offline tests for safe and bounded official GSC sitemap resubmission."""
import io
from pathlib import Path
from unittest.mock import patch
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gsc_sitemap_submit_test", ROOT / "seo/sitemap_submit.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


def sitemap(urls):
    return ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + ''.join('<url><loc>' + url + '</loc></url>' for url in urls)
            + '</urlset>').encode("utf-8")


def valid_urls():
    return [submit.SITE + '/', submit.SITE + '/directory', submit.SITE + '/categories/'] + [
        submit.SITE + '/blog/example-' + str(index) + '/' for index in range(15)
    ]


class Response:
    def __init__(self, body=b"", status=200, url=None):
        self.status = status
        self.body = io.BytesIO(body)
        self.url = url or submit.SITEMAP
    def read(self, count=-1):
        return self.body.read(count)
    def geturl(self):
        return self.url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None


class SitemapSubmitTests(unittest.TestCase):
    def test_valid_public_canonical_sitemap(self):
        self.assertEqual(submit.validate_public_sitemap(sitemap(valid_urls())), valid_urls())

    def test_reject_unexpected_host_duplicate_paths_and_missing_directory(self):
        cases = [
            valid_urls() + ['https://evil.invalid/example/'],
            valid_urls() + [valid_urls()[0]],
            [x for x in valid_urls() if x != submit.SITE + '/directory'],
            valid_urls() + [submit.SITE + '/about.html'],
            valid_urls() + [submit.SITE + '/blog/test/?q=1'],
        ]
        for urls in cases:
            with self.subTest(last=urls[-1]):
                with self.assertRaises(ValueError):
                    submit.validate_public_sitemap(sitemap(urls))

    def test_public_xml_redirect_rejected(self):
        request = []
        def fetch(req, timeout):
            request.append(req)
            return Response(sitemap(valid_urls()), url=submit.SITE + '/other.xml')
        with self.assertRaisesRegex(RuntimeError, "redirects away"):
            submit.fetch_xml(fetch)
        self.assertEqual(request[0].get_full_url(), submit.SITEMAP)

    def test_no_resubmission_after_successful_google_download(self):
        cases = [
            ([{'path': submit.SITEMAP, 'lastDownloaded': '2026-11-10T00:00:00Z'}], False),
            ([{'path': submit.SITEMAP, 'isPending': True}], True),
            ([], True),
            ([{'path': submit.SITEMAP, 'errors': 3}], True),
            ([{'path': submit.SITE + '/sitemap-v2.xml', 'lastDownloaded': '2026-10-24'}], True),
        ]
        for registered, expected in cases:
            with self.subTest(registered=registered):
                self.assertEqual(submit.should_submit(registered)[0], expected)

    def test_submit_only_put_to_exact_approved_sitemap(self):
        observed = []
        def fake(req, timeout):
            observed.append(req)
            return Response(b"", status=204)
        self.assertTrue(submit.submit_sitemap("test-token", fake))
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0].get_method(), "PUT")
        self.assertEqual(observed[0].get_header("Authorization"), "Bearer test-token")
        self.assertTrue(observed[0].full_url.endswith(
            '/sitemaps/https%3A%2F%2Flinkwiki.info%2Fsitemap.xml'))
        self.assertNotIn('indexing.googleapis.com', observed[0].full_url)

    def test_main_validates_before_authentication_or_any_write(self):
        with patch.object(submit, "fetch_xml", return_value=b"<not-sitemap/>"), \
             patch.object(submit, "authorization_token") as credentials, \
             patch.object(submit, "submit_sitemap") as send:
            with self.assertRaises(ValueError):
                submit.main()
        credentials.assert_not_called()
        send.assert_not_called()

    def test_successful_download_skips_mutation(self):
        with patch.object(submit, "fetch_xml", return_value=sitemap(valid_urls())), \
             patch.object(submit, "authorization_token", return_value="fake"), \
             patch.object(submit, "list_registered", return_value=[
                 {"path": submit.SITEMAP, "lastDownloaded": "2026-11-10T01:00:00Z"}]), \
             patch.object(submit, "submit_sitemap") as send:
            submit.main()
        send.assert_not_called()

    def test_pending_canonical_submits_once(self):
        with patch.object(submit, "fetch_xml", return_value=sitemap(valid_urls())), \
             patch.object(submit, "authorization_token", return_value="fake"), \
             patch.object(submit, "list_registered", return_value=[
                 {"path": submit.SITEMAP, "isPending": True}]), \
             patch.object(submit, "submit_sitemap") as send:
            submit.main()
        send.assert_called_once_with("fake")


if __name__ == "__main__":
    unittest.main()
