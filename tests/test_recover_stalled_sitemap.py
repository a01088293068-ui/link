from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import unittest
import xml.etree.ElementTree as ET

from seo import recover_stalled_sitemap as recovery


class SitemapRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 8, 4, tzinfo=timezone.utc)
        self.pending = {
            'path': recovery.SITEMAP, 'isPending': True,
            'lastSubmitted': '2026-10-27T06:35:03Z',
            'lastDownloaded': '', 'errors': '0', 'warnings': '0'
        }

    def test_week_old_pending_undownloaded_sitemap_is_eligible(self):
        self.assertTrue(recovery.eligible(self.pending, self.now)[0])
        for patch_data in (
                {'isPending': False},
                {'lastDownloaded': '2026-11-01T00:00:00Z'},
                {'lastSubmitted': '2026-11-07T01:00:00Z'},
                {'errors': '2'},
                {'path': 'https://another.example/sitemap.xml'},
                {'lastSubmitted': ''},
        ):
            with self.subTest(patch_data=patch_data):
                self.assertFalse(recovery.eligible({**self.pending, **patch_data}, self.now)[0])

    def test_only_verified_live_sitemap_is_resubmitted_once(self):
        def make_xml():
            root = ET.Element('urlset')
            for url in recovery.CORE_URLS:
                item = ET.SubElement(root, 'url')
                ET.SubElement(item, 'loc').text = url
                ET.SubElement(item, 'lastmod').text = '2026-11-08'
            return ET.tostring(root)
        good = make_xml()
        with TemporaryDirectory() as folder:
            dist = Path(folder)
            (dist / 'sitemap.xml').write_bytes(good)
            submit = Mock()
            result = recovery.recover('fake', dist, now=self.now,
                     list_fn=lambda token: [self.pending],
                     submit_fn=submit, fetch=lambda: good)
            self.assertIn('SUBMITTED:', result)
            submit.assert_called_once_with('fake')
            submit.reset_mock()
            outdated = good.replace(b'2026-11-08', b'2026-11-07')
            with self.assertRaisesRegex(RuntimeError, 'does not match'):
                recovery.recover('fake', dist, now=self.now,
                    list_fn=lambda token: [self.pending], submit_fn=submit,
                    fetch=lambda: outdated)
            submit.assert_not_called()
            result = recovery.recover('fake', dist, now=self.now,
                list_fn=lambda token: [{**self.pending, 'isPending': False}],
                submit_fn=submit, fetch=lambda: good)
            self.assertIn('SKIP:', result)
            submit.assert_not_called()

    def test_google_submit_uses_only_expected_url_and_put(self):
        class Response:
            status = 204
            def __enter__(self): return self
            def __exit__(self, *args): return False
        with patch.object(recovery, 'urlopen', return_value=Response()) as transport:
            recovery.submit_sitemap('fake-token')
        req = transport.call_args.args[0]
        self.assertEqual(req.get_method(), 'PUT')
        self.assertTrue(req.full_url.endswith('/https%3A%2F%2Flinkwiki.info%2Fsitemap.xml'))
        self.assertIn('sc-domain%3Alinkwiki.info', req.full_url)
        self.assertIsNone(req.data)


if __name__ == '__main__':
    unittest.main()
