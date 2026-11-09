"""Offline safety and semantics regression tests for listing health audit."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "seo/external_link_health.py"
spec = importlib.util.spec_from_file_location("external_link_health", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExternalLinkHealthTests(unittest.TestCase):
    def test_reject_private_hosts_credentials_and_non_https(self):
        bad = ("http://example.com", "https://localhost/", "https://127.0.0.1/",
               "https://10.0.0.1/", "https://user:secret@example.com/",
               "https://internal.local/", "file:///etc/passwd",
               "https://[::1]/", "https://example.com:8443/")
        for item in bad:
            with self.subTest(item=item):
                self.assertFalse(module.safe_url(item))
        self.assertTrue(module.safe_url("https://example.com/path?q=1"))

    def test_status_classification_does_not_call_bot_blocking_dead(self):
        self.assertEqual(module.classify(200), "reachable")
        self.assertEqual(module.classify(301), "redirect_review")
        self.assertEqual(module.classify(404), "broken_candidate")
        self.assertEqual(module.classify(410), "broken_candidate")
        self.assertEqual(module.classify(403), "restricted_or_unknown")
        self.assertEqual(module.classify(405), "restricted_or_unknown")
        self.assertEqual(module.classify(429), "restricted_or_unknown")
        self.assertEqual(module.classify(503), "server_error_unconfirmed")

    def test_invalid_url_does_not_open_network(self):
        def error_if_called(*args, **kwargs):
            raise AssertionError("Network must not be called")
        result = module.check_entry(
            {"name": "Local", "category": "test", "url": "https://127.0.0.1/"},
            opener=type("Fake", (), {"open": error_if_called})())
        self.assertEqual(result["status"], "invalid_url")

    def test_false_404_from_head_is_rechecked_using_get(self):
        from urllib.error import HTTPError
        class Response:
            status = 200
            headers = {}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        class MockOpener:
            methods = []
            def open(self, request, timeout=None):
                self.methods.append(request.get_method())
                if request.get_method() == "HEAD":
                    raise HTTPError(request.full_url, 404, "HEAD blocked", {}, None)
                return Response()
        opener = MockOpener()
        outcome = module.check_entry({"name": "working", "category": "한인교민",
                                      "url": "https://example.com/"}, opener)
        self.assertEqual(opener.methods, ["HEAD", "GET"])
        self.assertEqual(outcome["status"], "reachable")
        self.assertEqual(outcome["method"], "GET")

    def test_real_get_404_remains_only_candidate(self):
        from urllib.error import HTTPError
        class MockOpener:
            methods = []
            def open(self, request, timeout=None):
                self.methods.append(request.get_method())
                raise HTTPError(request.full_url, 404, "404", {}, None)
        opener = MockOpener()
        outcome = module.check_entry({"name": "unavailable", "category": "test",
                                      "url": "https://example.com/"}, opener)
        self.assertEqual(opener.methods, ["HEAD", "GET"])
        self.assertEqual(outcome["status"], "broken_candidate")
        self.assertEqual(outcome["method"], "GET")

    def test_report_is_candid_about_uncertain_statuses(self):
        text = module.markdown_report([
            {"name": "OK", "category": "AI", "url": "https://example.com",
             "http": "200", "status": "reachable", "redirect": "-"},
            {"name": "No HEAD", "category": "AI", "url": "https://example.net",
             "http": "403", "status": "restricted_or_unknown", "redirect": "-"},
        ], "2026-11-09 00:00 UTC")
        self.assertIn("restricted_or_unknown", text)
        self.assertIn("No entries are automatically modified", text)
        self.assertNotIn("| OK | AI |", text)

    def test_job_uses_only_recorded_source_and_generates_artifact(self):
        records = [{"name": "A", "category": "검색·포털", "url": "https://example.com"},
                   {"name": "B", "category": "스포츠", "url": "https://example.org"}]
        def fake(entry):
            return {**entry, "http": "200", "status": "reachable", "redirect": "-"}
        with TemporaryDirectory() as tmp:
            source, report = Path(tmp) / "records.json", Path(tmp) / "audit.md"
            source.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
            results = module.run(source=source, report=report, checker=fake)
            self.assertEqual(len(results), 2)
            self.assertIn("Checked:", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
