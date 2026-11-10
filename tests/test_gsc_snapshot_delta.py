"""Offline, privacy-safe regression tests for comparing authenticated GSC reports."""
import io
import json
import unittest
import zipfile

from seo.gsc_snapshot_delta import render, prior_snapshot


def report(*, date, verdict="NEUTRAL", coverage="크롤링됨 - 현재 색인이 생성되지 않음",
           crawl="2026-11-08T08:29:34Z", impressions=4):
    return {
        "schema": 1, "end_date": date,
        "inspections": [{
            "url": "https://linkwiki.info/directory", "verdict": verdict,
            "coverage": coverage, "last_crawl": crawl,
        }],
        "korea_core_weekly": [
            {"keyword": "링크모음",
             "recent": {"observed": True, "impressions": impressions,
                        "clicks": 1, "position": 123.0}},
            {"keyword": "주소모음", "recent": {"observed": False}},
            {"keyword": "사이트모음", "recent": {"observed": False}},
        ]
    }


class _FakeResponse:
    def __init__(self, value=None, content=b""):
        self.value, self.content = value, content
    def raise_for_status(self):
        pass
    def json(self):
        return self.value


class _FakeSession:
    def __init__(self, listing, archives):
        self.listing, self.archives = listing, archives
        self.calls = []
    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if url.endswith("/actions/artifacts"):
            return _FakeResponse(self.listing)
        return _FakeResponse(content=self.archives[url])


class GscDeltaTests(unittest.TestCase):
    def test_same_period_cannot_claim_rank_trend(self):
        past = report(date="2026-11-07", impressions=2)
        now = report(date="2026-11-07", impressions=4)
        text = render(now, past)
        self.assertIn("동일 집계 종료일 · 성과 추세 판정 불가", text)
        self.assertIn("크롤링 후", text)
        self.assertNotIn("순위 상승 확정", text)

    def test_real_new_crawl_and_verdict_are_separate(self):
        prior = report(date="2026-11-07")
        current = report(date="2026-11-08", verdict="PASS",
                         coverage="색인됨", crawl="2026-11-11T06:00:00Z")
        text = render(current, prior)
        self.assertIn("저장 크롤링 시각 갱신 · 색인 verdict 변경", text)
        self.assertIn("PASS / 색인됨", text)
        self.assertIn("NEUTRAL / 크롤링됨", text)

    def test_no_previous_does_not_erase_current_report(self):
        text = render(report(date="2026-11-07"), reason="최초 실행")
        self.assertIn("이전 자료 비교 불가", text)
        self.assertIn("최초 실행", text)

    def test_crawled_but_unindexed_is_not_indexed(self):
        text = render(report(date="2026-11-08"), report(date="2026-11-07"))
        self.assertIn("크롤링됨 - 현재 색인이 생성되지 않음", text)
        self.assertIn("새로운 크롤링 증거 없음", text)
        self.assertNotIn("색인 성공", text)

    def test_invalid_snapshot_schema_rejected(self):
        with self.assertRaises(ValueError):
            render({"schema": 2})

    def test_prior_artifact_excludes_current_run_and_reads_private_zip(self):
        prior = report(date="2026-11-06")
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as z:
            z.writestr("search-console-snapshot.json", json.dumps(prior))
        listing = {"artifacts": [
            {"name": "search-console-performance", "expired": False,
             "created_at": "2026-11-10T05:00:00Z",
             "workflow_run": {"id": 900},
             "archive_download_url": "https://example.test/current.zip",
             "size_in_bytes": 100},
            {"name": "search-console-performance", "expired": False,
             "created_at": "2026-11-09T05:00:00Z",
             "workflow_run": {"id": 800},
             "archive_download_url": "https://example.test/previous.zip",
             "size_in_bytes": len(memory.getvalue())},
        ]}
        session = _FakeSession(listing, {"https://example.test/previous.zip": memory.getvalue()})
        returned, url, error = prior_snapshot(session, "a01088293068-ui/link", 900)
        self.assertEqual(returned["end_date"], "2026-11-06")
        self.assertIn("/actions/runs/800", url)
        self.assertFalse(error)
        self.assertNotIn("https://example.test/current.zip", session.calls)

    def test_missing_private_artifact_is_not_fabricated(self):
        session = _FakeSession({"artifacts": []}, {})
        found, url, error = prior_snapshot(session, "a01088293068-ui/link", 1)
        self.assertIsNone(found)
        self.assertEqual(url, "")
        self.assertIn("없음", error)


if __name__ == "__main__":
    unittest.main()
