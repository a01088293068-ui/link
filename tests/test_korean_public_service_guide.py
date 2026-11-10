"""Keep the practical Korean public-service guide grounded in listed sites."""
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "content" / "seo-20261110-korean-public-services-guide.md"
DIRECTORY = ROOT / "assets" / "verified-directory.json"


class KoreanPublicServiceGuideTests(unittest.TestCase):
    def test_named_official_services_are_existing_directory_entries(self):
        markdown = GUIDE.read_text(encoding="utf-8")
        records = json.loads(DIRECTORY.read_text(encoding="utf-8"))
        listed_hosts = {urlsplit(item["url"]).hostname for item in records}
        outbound = re.findall(r"\]\((https://[^)]+)\)", markdown)
        self.assertGreaterEqual(len(outbound), 8)
        for url in outbound:
            with self.subTest(url=url):
                self.assertIn(urlsplit(url).hostname, listed_hosts)

    def test_guide_has_distinct_user_tasks_and_existing_internal_paths(self):
        markdown = GUIDE.read_text(encoding="utf-8")
        for label in ("정부24", "홈택스", "위택스", "복지로", "고용24",
                      "국민건강보험공단", "한국장학재단"):
            with self.subTest(label=label):
                self.assertIn(label, markdown)
        for path in ("/directory", "/categories/search", "/guides/address-check"):
            with self.subTest(path=path):
                self.assertIn("](" + path + ")", markdown)
        self.assertIn("실시간 서비스 상태", markdown)


if __name__ == "__main__":
    unittest.main()
