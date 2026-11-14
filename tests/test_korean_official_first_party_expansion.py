"""Guard the Korean-first public-service expansion against unverified or duplicate links."""
import json
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "티머니": ("https://www.tmoney.co.kr/", "생활·교통·여행"),
    "국립공원공단": ("https://www.knps.or.kr/", "생활·교통·여행"),
    "한국교육과정평가원": ("https://www.kice.re.kr/", "교육·취업"),
    "한국은행": ("https://www.bok.or.kr/", "금융·경제"),
    "문화체육관광부": ("https://www.mcst.go.kr/", "검색·포털"),
    "행정안전부": ("https://www.mois.go.kr/", "검색·포털"),
    "법제처": ("https://www.moleg.go.kr/", "검색·포털"),
    "국가인권위원회": ("https://www.humanrights.go.kr/", "검색·포털"),
    "한국환경공단": ("https://www.keco.or.kr/", "생활·교통·여행"),
    "국립중앙박물관": ("https://www.museum.go.kr/", "검색·포털"),
    "국립국어원": ("https://www.korean.go.kr/", "검색·포털"),
    "한국인터넷진흥원 KISA": ("https://www.kisa.or.kr/", "검색·포털"),
}


class KoreanOfficialFirstPartyExpansionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        cls.evidence = json.loads((ROOT / "assets/directory-evidence.json").read_text(encoding="utf-8"))

    def test_twelve_new_korean_destinations_are_unique_and_categorized(self):
        self.assertGreaterEqual(len(self.records), 335)
        self.assertEqual(len({row["name"] for row in self.records}), len(self.records))
        self.assertEqual(len({row["url"] for row in self.records}), len(self.records))
        by_name = {row["name"]: row for row in self.records}
        for name, (url, category) in EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["url"], url)
                self.assertEqual(by_name[name]["category"], category)
                self.assertTrue(by_name[name]["description"].endswith("세요."))
                self.assertGreaterEqual(len(by_name[name]["description"]), 65)

    def test_every_new_record_has_current_first_party_evidence(self):
        evidence_by_url = {row["url"]: row for row in self.evidence}
        for name, (url, _) in EXPECTED.items():
            with self.subTest(name=name):
                row = evidence_by_url[url]
                self.assertEqual(row["name"], name)
                self.assertEqual(row["source_url"], url)
                self.assertEqual(row["evidence_type"], "service_page")
                self.assertEqual(row["checked_on"], "2026-11-14")
                self.assertEqual(row["freshness_days"], 180)

    def test_all_new_sites_render_in_the_full_directory(self):
        built = ROOT / "dist/directory.html"
        if not built.exists():
            self.skipTest("Integrated build.py must run before generated HTML assertion")
        html = built.read_text(encoding="utf-8")
        for name, (url, _) in EXPECTED.items():
            with self.subTest(name=name):
                self.assertIn(name, html)
                self.assertIn(url, html)
