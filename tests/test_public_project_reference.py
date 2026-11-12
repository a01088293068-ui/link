"""Ensure public project docs actually link to the real directory landing."""
from pathlib import Path
import importlib.util
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("public_citation", ROOT/"seo"/"backlink-public-check.py")
checker=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

class ProjectReferenceTests(unittest.TestCase):
    def test_readme_has_actual_directory_hyperlink_and_usage(self):
        readme=(ROOT/"README.md").read_text(encoding="utf-8")
        self.assertIn("[사이트 주소모음 전체 목록 검색·두 사이트 비교](https://linkwiki.info/directory)",readme)
        self.assertIn("https://linkwiki.info/categories/",readme)
        self.assertIn("https://linkwiki.info/about",readme)
        self.assertIn("제3자의 독립적인 추천",readme)
        self.assertNotIn("Google 1위",readme)
    def test_git_repo_is_self_authored_not_independent_endorsement(self):
        url=checker.SITES["GitHub public project README (self-authored)"]
        self.assertEqual(url,"https://github.com/a01088293068-ui/link")
        html=b'<a href="https://linkwiki.info/directory">Open directory</a>'
        row=checker.check_one("GitHub project README",url,lambda _: (200,url,html))
        self.assertEqual(row["state"],"public_link_found")
        self.assertEqual(row["targets"],["/directory"])
    def test_readme_does_not_disclose_secrets(self):
        readme=(ROOT/"README.md").read_text(encoding="utf-8")
        for token in ("GOOGLE_SERVICE_ACCOUNT_JSON=", "GEMINI_API_KEY=", "backup.key", "PRIVATE KEY-----"):
            self.assertNotIn(token,readme)
    def test_link_is_only_to_canonical_site(self):
        readme=(ROOT/"README.md").read_text(encoding="utf-8")
        self.assertNotIn("https://linkwiki.info/directory.html",readme)
        self.assertNotIn("http://linkwiki.info",readme)
if __name__=="__main__":
    unittest.main()
