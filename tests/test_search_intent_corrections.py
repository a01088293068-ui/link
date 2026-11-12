"""Regression tests for search-result evidence tracking and real user corrections."""
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

import build
from seo import search_console_monitor as monitor

ROOT = Path(__file__).resolve().parents[1]


class SearchIntentAndCorrectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))

    def test_correction_form_is_user_facing_and_does_not_claim_verified_badges(self):
        markup = build.directory_address_correction_request(self.records)
        self.assertIn("주소가 바뀌었거나 설명이 틀렸나요?", markup)
        self.assertIn('id="directory-correction-request"', markup)
        self.assertIn('href="https://t.me/linkwiki_info"', markup)
        self.assertIn('href="/about"', markup)
        self.assertIn("공식 페이지 근거", markup)
        self.assertIn("확인 날짜", markup)
        self.assertIn("비밀번호·인증번호·결제정보", markup)
        self.assertNotIn("<form", markup)
        self.assertNotIn("검증 완료", markup)
        self.assertNotIn("자동 변경", markup.split("제보만으로", 1)[0])

    def test_correction_requires_real_directory_records(self):
        for sample in ([], [{}], None):
            with self.subTest(sample=sample), self.assertRaises(RuntimeError):
                build.directory_address_correction_request(sample)

    def test_live_build_links_to_correction_before_full_static_catalog(self):
        dist = ROOT / "dist" / "directory.html"
        if not dist.exists():
            self.skipTest("Run build.py before checking integrated HTML")
        html = dist.read_text(encoding="utf-8")
        self.assertEqual(html.count('id="directory-correction-request"'), 1)
        self.assertEqual(html.count('href="#directory-correction-request"'), 1)
        self.assertLess(html.index('href="#directory-correction-request"'),
                        html.index('id="v6-results"'))
        self.assertLess(html.index('id="v6-results"'),
                        html.index('id="directory-correction-request"'))
        self.assertEqual(html.count('<article class="v6-card" id="site-'), 222)
        self.assertIn('href="https://linkwiki.info/directory" rel="canonical"', html)

    def test_daily_rotation_survives_legacy_url_quota_pressure(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = root / "content"
            content.mkdir()
            for index in range(17):
                (content / f"seo-20261111-original-{index:02}.md").write_text(
                    "# 실사이트 검색 비교\n" + "공식 링크 및 활용 방법에 대한 설명. " * 12,
                    encoding="utf-8")
            original = [
                {"keys": [f"https://linkwiki.info/guides/legacy-{index}.html"],
                 "impressions": 100 - index}
                for index in range(30)
            ]
            exact = [
                {"keys": ["주소모음", "https://linkwiki.info/guides/choose-directory"],
                 "impressions": 4},
                {"keys": ["링크모음", "https://linkwiki.info/guides/link-faq"],
                 "impressions": 3},
            ]
            with patch.object(monitor, "ROOT", root):
                first = date(2026, 11, 12)
                result = monitor.inspection_targets(
                    original, limit=20, core_query_pages=exact, as_of=first)
                rotating = monitor.rotating_inspection_urls(first, limit=2, root=root)
                self.assertTrue(all(url in result for url in rotating))
                self.assertIn("https://linkwiki.info/directory", result)
                self.assertIn("https://linkwiki.info/guides/choose-directory", result)
                self.assertIn("https://linkwiki.info/guides/link-faq", result)
                self.assertEqual(len(result), 20)
                self.assertEqual(len(set(result)), 20)

    def test_rotation_moves_over_days_without_repeating_fictitious_urls(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = root / "content"
            content.mkdir()
            for index in range(11):
                (content / f"seo-20261111-service-{index:02}.md").write_text(
                    "# 설명\n" + "검증된 사이트 설명에 근거한 선택 기준. " * 12, encoding="utf-8")
            found = set()
            with patch.object(monitor, "ROOT", root):
                for i in range(6):
                    as_of = date(2026, 11, 11) + timedelta(days=i)
                    selection = monitor.inspection_targets([], as_of=as_of)
                    rotating = monitor.rotating_inspection_urls(as_of, limit=2, root=root)
                    self.assertTrue(all(url in selection for url in rotating))
                    found.update(rotating)
            self.assertEqual(len(found), 11)


if __name__ == "__main__":
    unittest.main()
