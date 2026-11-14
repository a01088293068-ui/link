import json
import unittest
from datetime import date
from pathlib import Path

import build


ROOT = Path(__file__).resolve().parents[1]


class DirectoryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.evidence = build.load_directory_evidence(cls.records)

    def test_source_records_match_published_sites_and_do_not_claim_unchecked_items(self):
        self.assertGreaterEqual(len(self.evidence), 23)
        for url, row in self.evidence.items():
            self.assertEqual(url, row["url"])
            self.assertLessEqual(date.fromisoformat(row["checked_on"]), date.today())

    def test_source_and_check_date_are_visible_on_directory_cards(self):
        html = build.render_directory_catalog_cards(
            self.records, self.evidence, today=date(2026, 11, 14))
        self.assertEqual(len(self.evidence), html.count('class="directory-evidence"'))
        self.assertIn("2026-11-14", html)
        self.assertIn("서비스 페이지와 등록 주소 대조", html)
        self.assertIn("관련 기관 안내의 연결 주소 대조", html)
        self.assertNotIn("공식 출처 안내 대조", html)
        self.assertIn("https://www.scourt.go.kr/work2025/helpinfo.html", html)
        self.assertIn("2025-01-31", html)
        self.assertIn("재확인 권고일 2027-05-13", html)

    def test_first_party_sources_cover_additional_public_services(self):
        expected = {
            "https://www.gov.kr/", "https://www.hometax.go.kr/",
            "https://www.work24.go.kr/", "https://www.nhis.or.kr/nhis/index.do",
            "https://www.nps.or.kr/main.do", "https://www.safedriving.or.kr/",
            "https://www.ebsi.co.kr/", "https://www.data.go.kr/",
            "https://kosis.kr/index/index.do", "https://www.schoolinfo.go.kr/Main.do",
        }
        self.assertTrue(expected.issubset(self.evidence))
        self.assertTrue(all(self.evidence[url]["evidence_type"] == "service_page" for url in expected))

    def test_old_source_evidence_expires_instead_of_appearing_current(self):
        html = build.render_directory_catalog_cards(
            self.records, self.evidence, today=date(2027, 6, 1))
        self.assertIn("근거 재확인 필요", html)
        self.assertNotIn("재확인 권고일 2027-05-13", html)

    def test_new_catalog_sites_flow_into_editorial_category_grid(self):
        template = (
            '<main><div class="v6-grid"><article class="v6-card">old</article></div>'
            '<section class="seo-guidance">분야별 이용 안내</section></main>')
        records = [
            {"name": "새 공공 서비스", "url": "https://public.example.kr/",
             "category": "커뮤니티", "description": "공식 서비스 설명"},
            {"name": "새 교육 서비스", "url": "https://learn.example.kr/",
             "category": "커뮤니티", "description": "학습 정보를 찾는 곳"},
        ]
        html = build.sync_category_card_copy(template, records, "커뮤니티")
        self.assertIn('href="https://public.example.kr/"', html)
        self.assertIn('href="https://learn.example.kr/"', html)
        self.assertEqual(2, html.count('class="v6-card"'))
        self.assertIn("분야별 이용 안내", html)

    def test_each_primary_search_intent_has_its_own_useful_task(self):
        html = build.directory_keyword_intents(self.records)
        self.assertIn('id="intent-address-collection"', html)
        self.assertIn('id="intent-link-collection"', html)
        self.assertIn('id="intent-site-collection"', html)
        self.assertIn("현재 작동 여부", html)


if __name__ == "__main__":
    unittest.main()
