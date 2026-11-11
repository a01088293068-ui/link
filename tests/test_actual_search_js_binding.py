"""Prevent erroneous failed public release checks from nonexistent JS APIs."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ActualSearchScriptBindingTests(unittest.TestCase):
    def test_qa_expects_real_search_function_usage(self):
        actual = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        verifier = (ROOT / "seo/live_release_check.py").read_text(encoding="utf-8")
        self.assertIn("const search = window.LinkWikiSearch;", actual)
        self.assertIn("search.sortResults(", actual)
        self.assertIn('"const search = window.LinkWikiSearch;" not in live_script', verifier)
        self.assertIn('"search.sortResults(" not in live_script', verifier)
        self.assertNotIn('"window.LinkWikiSearch.sortResults" not in live_script', verifier)

    def test_generated_search_script_remains_crawlable_and_local(self):
        actual = (ROOT / "assets/directory.js").read_text(encoding="utf-8")
        self.assertIn("querySelectorAll('article.v6-card')", actual)
        self.assertIn("search.sortResults(selected.map(entry => entry.site), query)", actual)
        self.assertNotIn("fetch(", actual)


if __name__ == "__main__":
    unittest.main()
