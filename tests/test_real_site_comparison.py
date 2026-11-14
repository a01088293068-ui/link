"""Test the actual catalog-backed two-site comparison, not a generated rating."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

from build import directory_two_site_comparison

ROOT = Path(__file__).resolve().parents[1]


class RealSiteComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))

    def test_panel_uses_the_verified_directory_catalog(self):
        output = directory_two_site_comparison(self.records)
        self.assertEqual(len(self.records), 279)
        self.assertIn('id="directory-two-site-compare"', output)
        for element in ("lw-site-compare-form", "lw-site-compare-first",
                        "lw-site-compare-second", "lw-site-compare-result"):
            self.assertEqual(output.count('id="' + element + '"'), 1)
        self.assertIn("등록 정보만 이용", output)
        self.assertNotIn('data-score=', output)
        self.assertNotIn('공식 인증된 사이트', output)

    def test_missing_catalog_fails_closed(self):
        for records in ([], [{}], None):
            with self.subTest(records=records):
                with self.assertRaises(RuntimeError):
                    directory_two_site_comparison(records)

    def test_generated_directory_has_one_compare_panel_and_279_original_cards(self):
        path = ROOT / "dist/directory.html"
        if not path.is_file():
            self.skipTest("Build first")
        html = path.read_text(encoding="utf-8")
        self.assertEqual(html.count('id="directory-two-site-compare"'), 1)
        self.assertEqual(html.count('href="#directory-two-site-compare"'), 1)
        self.assertEqual(html.count('<article class="v6-card"'), len(self.records))
        self.assertEqual(len(re.findall(r'<script[^>]*src="/assets/site-comparison.js\?v=[a-f0-9]{12}"', html)), 1)
        self.assertLess(html.index('id="v6-results"'), html.index('id="directory-two-site-compare"'))
        search_script = re.search(r'src="/?assets/directory\.js\?', html)
        self.assertIsNotNone(search_script)
        self.assertLess(html.index('src="/assets/site-comparison.js?'),
                        search_script.start())
        self.assertIn('role="status" aria-live="polite"', html)

    def test_comparison_js_is_local_and_uses_existing_static_cards(self):
        js = (ROOT / "assets/site-comparison.js").read_text(encoding="utf-8")
        self.assertIn("querySelectorAll('article.v6-card')", js)
        self.assertIn("const result = compareSites(one, two)", js)
        self.assertIn("replaceChildren", js)
        self.assertIn("field.replaceChildren(placeholder)", js)
        self.assertNotIn("field.append(placeholder)", js)
        self.assertIn("textContent", js)
        self.assertNotIn("fetch(", js)
        self.assertNotIn("XMLHttpRequest", js)
        self.assertNotIn("innerHTML", js)

    def test_real_service_pair_and_untrusted_url_rejected_by_node(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js unavailable")
        script = r"""
const assert = require('node:assert/strict');
const {compareSites, normalizedSite} = require('./assets/site-comparison.js');
const a = {name:'네이버 지도',category:'검색·포털',url:'https://map.naver.com/',
           description:'한국 내 지도와 길찾기'};
const b = {name:'DeepL',category:'AI 도구',url:'https://www.deepl.com/translator',
           description:'다국어 번역'};
const same = compareSites(a, a);
assert.equal(same.ok, false);
const result = compareSites(a, b);
assert.equal(result.ok, true);
assert.equal(result.sameCategory, false);
assert.equal(result.sites[0].host, 'map.naver.com');
assert.equal(result.sites[1].host, 'www.deepl.com');
assert.ok(result.note.includes('등록 항목'));
assert.equal(compareSites({...a,url:'javascript:alert(1)'}, b).ok, false);
assert.equal(compareSites({...a,url:'https://evil.com@unknown.example/'}, b).ok, false);
assert.equal(normalizedSite(null), null);
console.log('PASS site comparison DOM-data logic');
"""
        proc = subprocess.run([node, "-e", script], cwd=ROOT, text=True,
                              capture_output=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PASS", proc.stdout)

    def test_mobile_compare_css_layout(self):
        css = (ROOT / "assets/style.css").read_text(encoding="utf-8")
        self.assertIn(".lw-site-compare-grid", css)
        self.assertIn("@media(max-width:680px)", css)
        self.assertIn("#lw-site-compare-form", css)


if __name__ == "__main__":
    unittest.main()
