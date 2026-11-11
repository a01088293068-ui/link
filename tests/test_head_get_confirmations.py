"""Realistic HEAD/GET discrepancy handling for public directory records."""
import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("link_head_get", ROOT / "seo/observe_external_links.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MockResponse:
    def __init__(self, status):
        self.status = status
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class MockOpener:
    def __init__(self, codes):
        self.codes = iter(codes)
        self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        code = next(self.codes)
        if code >= 400:
            raise HTTPError(request.full_url, code, "status", {}, None)
        return MockResponse(code)


class HeadGetConfirmationTests(TestCase):
    def test_head_404_get_200_is_not_false_broken(self):
        opener = MockOpener([404, 200])
        result = mod.check_url("https://www.wolframalpha.com/", opener=opener)
        self.assertEqual(result["status"], "http_responded")
        self.assertEqual(result["http_code"], 200)
        self.assertEqual(result["head_http_code"], 404)
        self.assertEqual(result["confirmation_method"], "GET after HEAD 404/405")
        self.assertEqual([x.get_method() for x in opener.requests], ["HEAD", "GET"])
        self.assertEqual(opener.requests[1].get_header("Range"), "bytes=0-0")
        self.assertTrue(all(x.data is None for x in opener.requests))

    def test_head_405_get_206_range_is_accepted_as_http_response(self):
        opener = MockOpener([405, 206])
        result = mod.check_url("https://www.nate.com/", opener=opener)
        self.assertEqual(result["status"], "http_responded")
        self.assertEqual(result["http_code"], 206)

    def test_access_block_does_not_trigger_get_or_bypass(self):
        for status in (401, 403, 429, 451):
            with self.subTest(status=status):
                opener = MockOpener([status])
                result = mod.check_url("https://example.org/", opener=opener)
                self.assertEqual(result["status"], "access_limited")
                self.assertEqual(len(opener.requests), 1)

    def test_redirect_not_followed_and_does_not_get_retry(self):
        opener = MockOpener([302])
        result = mod.check_url("https://example.org/", opener=opener)
        self.assertEqual(result["status"], "redirect_review")
        self.assertEqual(len(opener.requests), 1)

    def test_head_404_get_404_stays_review_not_dead_label(self):
        opener = MockOpener([404, 404])
        result = mod.check_url("https://example.org/", opener=opener)
        self.assertEqual(result["status"], "http_error_review")
        self.assertEqual(result["head_http_code"], 404)
        self.assertEqual(result["get_http_code"], 404)
        self.assertIn("manual browser review", result["note"])
        self.assertEqual(len(opener.requests), 2)

    def test_head_405_get_403_does_not_look_verified(self):
        opener = MockOpener([405, 403])
        result = mod.check_url("https://example.org/", opener=opener)
        self.assertEqual(result["status"], "network_uncertain")
        self.assertEqual(result["get_http_code"], 403)
        self.assertNotIn("verified", json.dumps(result))

    def test_verified_kosis_official_landing_is_registered(self):
        records = mod.catalog_entries()
        item = next(x for x in records if x["name"] == "국가통계포털 KOSIS")
        self.assertEqual(item["url"], "https://kosis.kr/index/index.do")
        self.assertEqual(len(records), 222)
        self.assertEqual(len({x["url"] for x in records}), 222)


if __name__ == "__main__":
    import unittest
    unittest.main()
