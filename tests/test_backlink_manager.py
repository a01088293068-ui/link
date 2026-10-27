import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seo import backlink_manager as manager


class BacklinkManagerTests(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(manager.validate_url("https://example.com/path"), "https://example.com/path")
        for url in ("http://example.com", "https://127.0.0.1", "https://localhost", "file:///etc/passwd"):
            with self.assertRaises(ValueError):
                manager.validate_url(url)

    def test_html_audit(self):
        html = '<meta name="robots" content="index,follow"><a href="https://linkwiki.info/" rel="nofollow">LinkWiki</a>'
        result, found, rel, noindex = manager.evaluate_html(html, "linkwiki.info")
        self.assertEqual((result, found, rel, noindex), ("link_with_rel", True, ["nofollow"], False))
        result, found, rel, noindex = manager.evaluate_html('<a href="https://linkwiki.info/">사이트</a>', "linkwiki.info")
        self.assertEqual(result, "verified_link")
        result, found, rel, noindex = manager.evaluate_html('<meta name="robots" content="noindex"><a href="https://linkwiki.info">x</a>', "linkwiki.info")
        self.assertEqual(result, "noindex")
        result, found, rel, noindex = manager.evaluate_html('<a href="https://fake-linkwiki.info">x</a>', "linkwiki.info")
        self.assertEqual(result, "missing_link")

    def test_csv_idempotent_and_public_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.csv"
            path.write_text("platform,submission_url,public_url,submission_status\nExample,https://example.com/submit,https://example.com/list,submitted\n", encoding="utf-8")
            registry = manager.load_registry(Path(folder) / "ledger.json")
            self.assertEqual(manager.import_csv(registry, path), (1, 0))
            self.assertEqual(manager.import_csv(registry, path), (0, 1))
            with patch.object(manager, "fetch_public", return_value=(200, '<a href="https://linkwiki.info/">LinkWiki</a>', "", "text/html")):
                self.assertEqual(manager.audit(registry), 1)
            self.assertEqual(registry["entries"][0]["audit_status"], "verified_link")
            self.assertIn("verified_link", manager.markdown_report(registry))


if __name__ == "__main__":
    unittest.main()
