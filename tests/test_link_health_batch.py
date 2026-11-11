import unittest
from datetime import date, timedelta
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from seo.link_health_batch import daily_batch, observe, render, safe_public_host


def fake_dns(ip):
    return lambda *args, **kw: [(2, 1, 0, "", (ip, 443))]


class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): pass


class LinkHealthBatchTests(unittest.TestCase):
    def test_public_https_only_rejects_private_and_invalid_destinations(self):
        self.assertTrue(safe_public_host("https://example.com/",resolve=fake_dns("8.8.8.8")))
        for url in ("http://example.com/", "https://localhost/",
                    "https://127.0.0.1/", "https://example.com:8443/",
                    "https://private.internal/", "https://user:pass@example.com/",
                    "https://example.com/#section"):
            self.assertFalse(safe_public_host(url,resolve=fake_dns("8.8.8.8")))
        for ip in ("127.0.0.1", "10.0.0.3", "192.168.1.8", "172.16.0.9", "::1",
                   "169.254.169.254", "100.64.0.1"):
            self.assertFalse(safe_public_host("https://example.com/",resolve=fake_dns(ip)))

    def test_daily_batches_are_bounded_and_cover_all_records(self):
        rows = [{"name":str(i), "url":f"https://example{i}.com/"} for i in range(211)]
        first = date(2026,11,11)
        batches=[daily_batch(rows, first+timedelta(days=i)) for i in range(6)]
        self.assertTrue(all(len(b) == 36 for b in batches))
        self.assertEqual(len({x["url"] for b in batches for x in b}),211)
        self.assertRaises(ValueError, daily_batch, rows,first,37)
        self.assertEqual(daily_batch([],first),[])

    def test_does_not_follow_redirect_or_retry_restricted_head(self):
        client=Mock()
        client.open.side_effect=HTTPError("https://example.com/",302,"redirect",{},None)
        output=observe("https://example.com/",checker=lambda url: True,opener=client)
        self.assertEqual(output,{"status":"redirect_manual_review","http":302})
        self.assertEqual(client.open.call_count,1)
        client.open.side_effect=HTTPError("https://example.com/",405,"unsupported",{},None)
        self.assertEqual(observe("https://example.com/",checker=lambda url: True,opener=client)["status"],
                         "head_blocked_or_unsupported")
        client.open.side_effect=URLError("offline")
        self.assertEqual(observe("https://example.com/",checker=lambda url: True,opener=client)["status"],
                         "network_unverified")
        client.open.side_effect=None
        client.open.return_value=FakeResponse()
        self.assertEqual(observe("https://example.com/",checker=lambda url: True,opener=client)["status"],
                         "head_responded")

    def test_private_report_never_calls_url_healthy_or_safety_ranking(self):
        row={"name":"Example","url":"https://example.com/"}
        text=render([row],[(row,{"status":"head_responded","http":200})],date(2026,11,11))
        self.assertIn("HEAD 요청",text)
        self.assertIn("안전성",text)
        self.assertIn("example.com",text)
        self.assertNotIn("정상 사이트로 인증",text)


if __name__ == "__main__":
    unittest.main()
