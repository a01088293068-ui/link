"""Offline tests for safe sitemap deployment waits and official GSC submission."""
import io
import tempfile
from pathlib import Path
from unittest.mock import patch
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gsc_sitemap_submit_test", ROOT / "seo/sitemap_submit.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


def sitemap(urls, lastmods=None):
    lastmods = lastmods or {}
    rows = []
    for url in urls:
        lastmod = lastmods.get(url)
        extra = '<lastmod>' + lastmod + '</lastmod>' if lastmod else ''
        rows.append('<url><loc>' + url + '</loc>' + extra + '</url>')
    return ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + ''.join(rows) + '</urlset>').encode("utf-8")


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

    def test_expected_deployed_urls_must_be_present(self):
        with self.assertRaisesRegex(ValueError, "required deployed SEO URL missing"):
            submit.validate_public_sitemap(
                sitemap(valid_urls()),
                required_urls=(submit.SITE + "/blog/new-guide/",))

    def test_expected_public_urls_come_from_published_source_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "categories").mkdir()
            (root / "guides").mkdir()
            (root / "content").mkdir()
            (root / "categories" / "education.html").write_text("<h1>Education</h1>")
            (root / "categories" / "index.html").write_text("<h1>Index</h1>")
            (root / "guides" / "address-check.html").write_text("<h1>Guide</h1>")
            (root / "content" / "public-jobs.md").write_text("# Public jobs\n")
            (root / "content" / "draft.md").write_text("not published\n")
            expected = submit.expected_public_urls(root)
        self.assertEqual(expected, (
            submit.SITE + "/categories/education",
            submit.SITE + "/guides/address-check",
            submit.SITE + "/blog/public-jobs/",
        ))

    def test_latest_sitemap_lastmod_uses_newest_explicit_date(self):
        urls = valid_urls()
        xml = sitemap(urls, {
            urls[0]: "2026-11-10",
            urls[1]: "2026-11-16",
            urls[2]: "2026-11-12",
        })
        self.assertEqual(submit.latest_sitemap_lastmod(xml), "2026-11-16")
        self.assertIsNone(submit.latest_sitemap_lastmod(sitemap(urls)))

    def test_wait_for_live_deployment_to_publish_expected_urls(self):
        expected = submit.SITE + "/blog/new-guide/"
        stale = sitemap(valid_urls())
        deployed = sitemap(valid_urls() + [expected])
        with patch.object(submit, "fetch_xml", side_effect=[stale, deployed]) as fetch, \\
             patch.object(submit, "time") as clock:
            xml, urls = submit.fetch_deployed_sitemap(
                expected_urls=(expected,), attempts=3, delay_seconds=7)
        self.assertIn(expected, urls)
        self.assertEqual(fetch.call_count, 2)
        clock.sleep.assert_called_once_with(7)

    def test_deployment_wait_fails_closed_if_current_release_never_appears(self):
        expected = submit.SITE + "/blog/new-guide/"
        with patch.object(submit, "fetch_xml", return_value=sitemap(valid_urls())), \\
             patch.object(submit, "time") as clock:
            with self.assertRaisesRegex(RuntimeError, "did not catch up"):
                submit.fetch_deployed_sitemap(
                    expected_urls=(expected,), attempts=3, delay_seconds=5)
        self.assertEqual(clock.sleep.call_count, 2)

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

    def test_resubmit_only_when_sitemap_is_newer_than_google_download(self):
        current = {"path": submit.SITEMAP, "lastDownloaded": "2026-11-12T04:27:02Z"}
        self.assertEqual(submit.should_submit([current], "2026-11-16")[0], True)
        self.assertEqual(submit.should_submit([current], "2026-11-12")[0], False)
        self.assertEqual(submit.should_submit([current], "2026-11-10")[0], False)

    def test_pending_or_successfully_downloaded_current_sitemap_is_not_duplicated(self):
        cases = [
            ([{"path": submit.SITEMAP, "isPending": True}], False),
            ([], True),
            ([{"path": submit.SITEMAP, "errors": 3}], True),
            ([{"path": submit.SITE + "/sitemap-v2.xml", "lastDownloaded": "2026-10-24"}], True),
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

    def test_main_waits_for_deployed_urls_before_authentication_or_mutation(self):
        with patch.object(submit, "expected_public_urls", return_value=("/required/",)), \\
             patch.object(submit, "fetch_deployed_sitemap", side_effect=RuntimeError("stale")), \\
             patch.object(submit, "authorization_token") as credentials, \\
             patch.object(submit, "submit_sitemap") as send:
            with self.assertRaisesRegex(RuntimeError, "stale"):
                submit.main()
        credentials.assert_not_called()
        send.assert_not_called()

    def test_main_resubmits_after_newer_published_sitemap_update(self):
        xml = sitemap(valid_urls(), {valid_urls()[1]: "2026-11-16"})
        with patch.object(submit, "expected_public_urls", return_value=()), \\
             patch.object(submit, "fetch_deployed_sitemap", return_value=(xml, valid_urls())), \\
             patch.object(submit, "latest_sitemap_lastmod", return_value="2026-11-16"), \\
             patch.object(submit, "authorization_token", return_value="fake"), \\
             patch.object(submit, "list_registered", return_value=[
                 {"path": submit.SITEMAP, "lastDownloaded": "2026-11-12T04:27:00Z"}]), \\
             patch.object(submit, "submit_sitemap") as send:
            submit.main()
        send.assert_called_once_with("fake")

    def test_main_skips_when_google_downloaded_after_latest_published_update(self):
        xml = sitemap(valid_urls(), {valid_urls()[1]: "2026-11-12"})
        with patch.object(submit, "expected_public_urls", return_value=()), \\
             patch.object(submit, "fetch_deployed_sitemap", return_value=(xml, valid_urls())), \\
             patch.object(submit, "latest_sitemap_lastmod", return_value="2026-11-12"), \\
             patch.object(submit, "authorization_token", return_value="fake"), \\
             patch.object(submit, "list_registered", return_value=[
                 {"path": submit.SITEMAP, "lastDownloaded": "2026-11-12T04:27:00Z"}]), \\
             patch.object(submit, "submit_sitemap") as send:
            submit.main()
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
