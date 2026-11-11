"""Catch stale editorial evidence disclosures in the public release."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from email.message import Message
import unittest

from seo.live_release_check import check_page, fetch_public

SITE = "https://linkwiki.info"


class LiveEditorialProvenanceTests(unittest.TestCase):
    def test_stale_guide_disclosure_is_detected_without_body_difference(self):
        path = "/blog/seo-20261111-tax-hometax-wetax-difference/"
        head = ('<html><head><title>홈택스와 위택스</title>'
                f'<link rel="canonical" href="{SITE + path}"></head><body>')
        content = ('<h1>홈택스와 위택스</h1>'
                   '<div class="blog-content"><p>서로 다른 세금 업무를 다룹니다.</p></div>'
                   '<aside class="blog-source-note"><h2>이 글의 정보 기준</h2>'
                   '<p>등록 목록에 근거합니다.</p></aside>'
                   '<a href="/directory">목록</a>'
                   '<a href="/categories/">분야별</a>')
        expected = head + content + '</body></html>'
        stale = expected.replace('등록 목록에 근거합니다.', '이전 원칙으로 작성했습니다.')
        issues = check_page(expected, stale, path)
        self.assertTrue(any('editorial provenance differs' in s for s in issues), issues)
        self.assertFalse(any('guide body differs' in s for s in issues), issues)
        self.assertEqual(check_page(expected, expected, path), [])

    def test_missing_disclosure_does_not_pass(self):
        path = "/blog/example/"
        original = ('<html><head><title>가이드</title>'
                    f'<link rel="canonical" href="{SITE + path}"></head><body>'
                    '<h1>가이드</h1><div class="blog-content"><p>안내</p></div>'
                    '<aside class="blog-source-note">작성 근거</aside>'
                    '<a href="/directory">전체</a><a href="/categories/">분야</a>'
                    '</body></html>')
        result = check_page(original, original.replace(
            '<aside class="blog-source-note">작성 근거</aside>', ''), path)
        self.assertTrue(any('editorial provenance differs' in s for s in result))

    def test_stale_about_methodology_detected(self):
        path = "/about"
        base = ('<html><head><title>운영 안내</title>'
                f'<link rel="canonical" href="{SITE + path}"></head><body>'
                '<h1>운영 안내</h1><h2>글 작성과 정보 확인 범위</h2></body></html>')
        live = base.replace("글 작성과 정보 확인 범위", "이전 문서")
        self.assertIn("/about: editorial methodology not deployed", check_page(base, live, path))
        self.assertEqual(check_page(base, base, path), [])

    def test_about_canonical_redirect_is_detected(self):
        class Response:
            status = 200
            headers = Message()
            def geturl(self):
                return SITE + "/about.html"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("seo.live_release_check.urlopen", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "Canonical URL redirected"):
                fetch_public("/about")

    def test_live_release_checks_about_when_available(self):
        source = (Path(__file__).resolve().parents[1] / "seo/live_release_check.py").read_text()
        self.assertIn('expected_map["/about"] = dist / "about.html"', source)


if __name__ == "__main__":
    unittest.main()
