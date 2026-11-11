"""Catch stale comparison JS/panel in the live LinkWiki release."""
from pathlib import Path
import unittest

from seo.live_release_check import check_page, run

ROOT = Path(__file__).resolve().parents[1]


class SiteCompareReleaseTests(unittest.TestCase):
    def test_live_comparison_panel_cannot_disappear_silently(self):
        dist = ROOT / "dist"
        if not (dist / "directory.html").exists():
            self.skipTest("Run build first")
        expected = (dist / "directory.html").read_text(encoding="utf-8")
        import re
        older = re.sub(
            r'<section[^>]*id="directory-two-site-compare"[^>]*>.*?</section>',
            '', expected, count=1, flags=re.S
        )
        self.assertNotEqual(expected, older)
        issues = check_page(expected, older, "/directory")
        self.assertTrue(any("deployed directory examples differ" in x for x in issues))

    def test_live_compare_script_changes_get_detected(self):
        dist = ROOT / "dist"
        if not (dist / "assets/site-comparison.js").is_file():
            self.skipTest("Run build first")
        from seo.live_release_check import CATEGORY_PATHS
        source = (dist / "assets/site-comparison.js").read_text(encoding="utf-8")
        def fetch(path):
            if path == "/assets/site-comparison.js":
                return source.replace("field.replaceChildren(placeholder)", "field.append(placeholder)")
            if path.startswith("/assets/") or path in ("/robots.txt", "/sitemap.xml", "/sitemap-v2.xml"):
                return (dist / path.lstrip("/")).read_text(encoding="utf-8")
            if path == "/":
                return (dist / "index.html").read_text(encoding="utf-8")
            if path == "/directory":
                return (dist / "directory.html").read_text(encoding="utf-8")
            if path == "/categories/":
                return (dist / "categories/index.html").read_text(encoding="utf-8")
            if path == "/about":
                return (dist / "about.html").read_text(encoding="utf-8")
            if path in CATEGORY_PATHS:
                return (dist / "categories" / (path.rsplit("/", 1)[-1] + ".html")).read_text(encoding="utf-8")
            if path.startswith("/blog/"):
                return (dist / "blog" / path.strip("/").split("/")[-1] / "index.html").read_text(encoding="utf-8")
            raise AssertionError("unexpected URL: " + path)
        issues = run(dist, fetch=fetch)
        self.assertTrue(any("deployed comparison logic differs" in x for x in issues), issues)


if __name__ == "__main__":
    unittest.main()
