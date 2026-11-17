"""Keep primary directory navigation on its canonical extensionless URL."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DirectoryCanonicalLinkTests(unittest.TestCase):
    def test_homepage_and_directory_do_not_link_to_redirecting_html_alias(self):
        for relative in ("index.html", "directory.html", "about.html"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(page=relative):
                self.assertNotRegex(
                    source,
                    r'href=["\'](?:\./)?directory\.html(?:[?#][^"\']*)?["\']',
                    "Internal links must point directly to canonical /directory.",
                )

    def test_primary_navigation_links_directly_to_canonical_directory(self):
        for relative in ("index.html", "directory.html", "about.html"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(page=relative):
                self.assertIn('href="/directory"', source)


if __name__ == "__main__":
    unittest.main()
