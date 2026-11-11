"""Ensure link-review reports are grounded in published records, never fake checks."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "seo"))
import observe_external_links as observe
import external_link_triage as triage


class ExternalLinkTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = observe.catalog_entries()

    def observations(self):
        responses = {
            "네이버": {"status": "http_responded", "http_code": 200},
            "다음": {"status": "http_error_review", "http_code": 404},
            "Brave Search": {"status": "access_limited", "http_code": 429},
            "Swisscows": {"status": "redirect_review", "http_code": 307},
        }
        result = observe.run(date(2026, 11, 11), self.records, batch_size=24,
                             observer=lambda url: next(
                                 (responses[row["name"]] for row in self.records
                                  if row["url"] == url and row["name"] in responses),
                                 {"status": "http_responded", "http_code": 200}))
        return result

    def test_24_real_names_and_non_success_list_appear_in_review(self):
        snapshot = self.observations()
        rendered = triage.render(snapshot, self.records)
        for name in ("다음", "Brave Search", "Swisscows"):
            self.assertIn(name, rendered)
        self.assertIn("404", rendered)
        self.assertIn("429", rendered)
        self.assertIn("307", rendered)
        self.assertIn("HTTP 응답 관찰 목록 (미검증)", rendered)
        self.assertIn("한 번의 관찰만으로 링크를 삭제하거나 수정하지 않습니다", rendered)
        self.assertIn("222개 중 24개", rendered)
        self.assertIn("GET으로 확인", rendered)
        self.assertIn("우회하거나 반복 요청하지 않습니다", rendered)

    def test_cannot_insert_fake_unpublished_site(self):
        snapshot = self.observations()
        snapshot["results"][0]["url"] = "https://fake-unlisted.example/"
        with self.assertRaisesRegex(ValueError, "not in published catalog"):
            triage.render(snapshot, self.records)

    def test_duplicate_and_count_mismatch_rejected(self):
        snapshot = self.observations()
        snapshot["results"].append(deepcopy(snapshot["results"][0]))
        snapshot["checked_count"] += 1
        with self.assertRaisesRegex(ValueError, "duplicate observed URL"):
            triage.render(snapshot, self.records)
        snapshot["checked_count"] -= 2
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            triage.render(snapshot, self.records)

    def test_changed_name_or_status_rejected(self):
        snapshot = self.observations()
        snapshot["results"][0]["name"] = "허위 검증 사이트"
        with self.assertRaisesRegex(ValueError, "differs from catalog"):
            triage.render(snapshot, self.records)
        snapshot = self.observations()
        snapshot["results"][0]["observation"]["status"] = "verified_safe"
        with self.assertRaisesRegex(ValueError, "unsupported observation status"):
            triage.render(snapshot, self.records)

    def test_html_and_markdown_markup_do_not_expand_report_tables(self):
        item = dict(self.records[0], name="bad | table\ntext")
        rows = [item]
        snapshot = {
            "date_utc": "2026-11-11", "checked_count": 1,
            "catalog_count": 1,
            "results": [{
                "name": item["name"], "category": item["category"],
                "url": item["url"],
                "observation": {"status": "http_responded", "http_code": 200}
            }],
        }
        report = triage.render(snapshot, rows)
        self.assertIn("bad ∣ table text", report)
        self.assertNotIn("bad | table", report)

    def test_only_http_response_not_assumed_functioning(self):
        report = triage.render(self.observations(), self.records)
        self.assertNotIn("정상 작동 검증 완료", report)
        self.assertNotIn("안전한 사이트 인증", report)
        self.assertIn("실사용 가능, 공식 소유권, 안전 여부의 증거가 아닙니다", report)


if __name__ == "__main__":
    unittest.main()
