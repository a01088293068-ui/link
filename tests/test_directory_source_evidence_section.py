import json
import unittest
from pathlib import Path

from build import directory_source_evidence_section, load_directory_evidence


ROOT = Path(__file__).resolve().parents[1]


class DirectorySourceEvidenceSectionTests(unittest.TestCase):
    def test_section_lists_only_source_backed_catalog_records(self):
        records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        evidence = load_directory_evidence(records)
        html = directory_source_evidence_section(records, evidence)

        self.assertIn("공식 출처와 대조한 사이트 주소 기록", html)
        self.assertIn(f"공개 목록 {len(records)}개 중 {len(evidence)}건의 항목", html)
        self.assertEqual(html.count('class="source-evidence-row"'), len(evidence))
        for url, row in evidence.items():
            self.assertIn(row["name"], html)
            self.assertIn(row["source_url"], html)
            self.assertIn(row["checked_on"], html)
        self.assertIn("현재 접속 가능 여부", html)
        self.assertIn("아래에 표시되지 않은 항목은 이 출처 대조 기록에 포함되지 않았습니다.", html)

    def test_empty_evidence_does_not_claim_verification(self):
        records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
        self.assertEqual(directory_source_evidence_section(records, {}), "")


if __name__ == "__main__":
    unittest.main()
