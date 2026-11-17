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

    def test_additional_education_and_qualification_sites_have_first_party_sources(self):
        expected = {
            "https://www.hrdkorea.or.kr/": "agency_guide",
            "https://www.historyexam.go.kr/": "service_page",
            "https://www.cb.or.kr/": "agency_guide",
            "https://www.academyinfo.go.kr/": "agency_guide",
            "https://www.krivet.re.kr/": "agency_guide",
            "https://www.q-net.or.kr/": "service_page",
        }
        for url, evidence_type in expected.items():
            with self.subTest(url=url):
                self.assertIn(url, self.evidence)
                self.assertEqual(self.evidence[url]["evidence_type"], evidence_type)
                self.assertLessEqual(
                    date.fromisoformat(self.evidence[url]["checked_on"]), date.today()
                )
                self.assertTrue(self.evidence[url]["source_url"].startswith("https://"))

    def test_housing_finance_agency_source_is_first_party(self):
        row = self.evidence["https://www.hf.go.kr/"]
        self.assertEqual(row["name"], "한국주택금융공사")
        self.assertEqual(row["evidence_type"], "agency_guide")
        self.assertEqual(row["source_url"], "https://www.hf.go.kr/ko/sub05/sub05_01_01.do")

    def test_additional_korean_public_services_have_first_party_evidence(self):
        expected = {
            "https://www.kca.go.kr/": "https://www.kca.go.kr/odr/pg/ma/pgProcssInfo.do",
            "https://www.bigkinds.or.kr/": "https://www.bigkinds.or.kr/",
            "https://www.nanet.go.kr/": "https://www.nanet.go.kr/usermadang/etc/infoUseReqView.do",
            "https://www.0404.go.kr/": "https://www.0404.go.kr/bbs/travelAlertAjmt/list",
            "https://rt.molit.go.kr/": "https://rt.molit.go.kr/",
            "https://www.car365.go.kr/": "https://www.car365.go.kr/",
            "https://www.culture.go.kr/": "https://www.culture.go.kr/portal/main/contents.do?menuNo=200095",
            "https://kopis.or.kr/por/main/main.do": "https://kopis.or.kr/por/main/main.do",
            "https://www.kinfa.or.kr/": "https://www.kinfa.or.kr/counselingSupport/centerIntroduction.do",
        }
        for url, source_url in expected.items():
            with self.subTest(url=url):
                self.assertIn(url, self.evidence)
                self.assertEqual(self.evidence[url]["source_url"], source_url)
                self.assertEqual(self.evidence[url]["evidence_type"], "service_page")
                self.assertEqual(self.evidence[url]["checked_on"], "2026-11-17")

    def test_remaining_official_finance_services_have_first_party_evidence(self):
        expected = {
            "https://www.kdic.or.kr/": ("https://www.kdic.or.kr/sp/main.do", "service_page"),
            "https://seibro.or.kr/": ("https://www.ksd.or.kr/ko/", "agency_guide"),
            "https://www.fss.or.kr/edu/main.jsp": ("https://www.fss.or.kr/edu/main/main.do", "service_page"),
        }
        for url, (source_url, evidence_type) in expected.items():
            with self.subTest(url=url):
                self.assertIn(url, self.evidence)
                self.assertEqual(self.evidence[url]["source_url"], source_url)
                self.assertEqual(self.evidence[url]["evidence_type"], evidence_type)
                self.assertEqual(self.evidence[url]["checked_on"], "2026-11-17")

    def test_korean_finance_and_market_research_services_have_first_party_evidence(self):
        expected = {
            "https://banking.nonghyup.com/": "https://banking.nonghyup.com/nhbank.html",
            "https://www.imbank.co.kr/": "https://www.imbank.co.kr/dgb_ebz_main.jsp",
            "https://www.kcmi.re.kr/": "https://www.kcmi.re.kr/",
            "https://data.krx.co.kr/": "https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd",
        }
        for url, source_url in expected.items():
            with self.subTest(url=url):
                self.assertIn(url, self.evidence)
                self.assertEqual(self.evidence[url]["source_url"], source_url)
                self.assertEqual(self.evidence[url]["evidence_type"], "service_page")
                self.assertEqual(self.evidence[url]["checked_on"], "2026-11-17")

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
