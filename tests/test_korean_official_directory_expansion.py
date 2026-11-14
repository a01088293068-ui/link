"""Official Korean sites and task navigation are actually published and distinct."""
import json
from pathlib import Path
from unittest import TestCase

from build import directory_task_paths

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "경찰청 사이버범죄 신고시스템 ECRM",
    "주소정보누리집 도로명주소",
    "대법원 인터넷등기소",
    "한국은행 경제통계시스템 ECOS",
    "대한민국 법원 전자소송포털",
    "에듀넷 티클리어",
    "국민안전24",
)


class VerifiedPublicServiceExpansionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))

    def test_actual_catalog_is_deduplicated_and_explained(self):
        self.assertEqual(len(self.records), 315)
        self.assertEqual(len({record["name"] for record in self.records}), len(self.records))
        self.assertEqual(len({record["url"] for record in self.records}), len(self.records))
        added = [entry for entry in self.records if entry["name"] in NAMES]
        self.assertEqual(len(added), len(NAMES))
        for entry in added:
            self.assertEqual(entry["category"], "검색·포털")
            self.assertTrue(entry["url"].startswith("https://"))
            self.assertGreaterEqual(len(entry["description"]), 50)

    def test_candidate_probe_records_51_checked_hosts_and_36_published_additions(self):
        evidence = json.loads(
            (ROOT / "seo/korean-site-candidate-checks-20261114.json").read_text(encoding="utf-8"))
        published = {record["url"] for record in self.records}
        added = [row for row in evidence["candidates"] if row["catalog_added"]]
        self.assertEqual(evidence["candidate_count"], 51)
        self.assertEqual(evidence["catalog_additions"], 36)
        self.assertEqual(len(added), 36)
        self.assertTrue(all(row["candidate_url"] in published for row in added))
        self.assertEqual(len({row["candidate_url"] for row in evidence["candidates"]}), 51)

    def test_sports_promotion_service_uses_the_sports_category(self):
        item = next(record for record in self.records
                    if record["name"] == "서울올림픽기념 국민체육진흥공단")
        self.assertEqual(item["category"], "스포츠")

    def test_task_paths_offer_real_named_destinations_and_practical_disambiguation(self):
        html = directory_task_paths(self.records)
        for name in NAMES:
            self.assertIn(name, html)
        for label in ("도로명주소 조회와 등기사항 확인", "경제지표와 범분야 공식 통계",
                      "사이버범죄 신고와 일반 민원", "전자소송과 법령 원문 확인",
                      "교수학습 자료와 고교강의"):
            self.assertIn(label, html)
        self.assertNotIn("안전 등급", html)

    def test_static_page_metadata_counts_match_catalog(self):
        for path in ("index.html", "directory.html"):
            original = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("315개", original)
            self.assertNotIn("222개", original)

    def test_build_produces_seven_actual_crawlable_public_service_cards(self):
        built = ROOT / "dist/directory.html"
        if not built.exists():
            self.skipTest("Integrated build.py must run before generated HTML assertion")
        html = built.read_text(encoding="utf-8")
        for name in NAMES:
            self.assertIn(name, html)
        self.assertEqual(html.count('<article class="v6-card" id="site-'), 315)
        self.assertIn("주소정보누리집 도로명주소", html)
        self.assertIn("국민안전24", html)
        self.assertIn("https://www.safekorea.go.kr/", html)
        self.assertIn('href="https://linkwiki.info/directory" rel="canonical"', html)
