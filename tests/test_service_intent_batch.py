"""Release coverage for five distinct Korean service-intent guides."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SLUGS = {
    "seo-20261111-tax-hometax-wetax-difference": ("국세청 홈택스", "위택스"),
    "seo-20261111-gov24-epeople-complaint-certificate": ("정부24", "국민신문고"),
    "seo-20261111-public-data-vs-kosis-usage": ("공공데이터포털", "KOSIS"),
    "seo-20261111-work24-scholarship-benefits-choice": ("고용24", "복지로"),
    "seo-20261111-korean-ai-write-translate-design": ("ChatGPT", "DeepL"),
}
SITE = "https://linkwiki.info"


class ServiceIntentBatchTests(unittest.TestCase):
    def test_all_five_guides_are_distinct_and_use_verified_services(self):
        import json
        records = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
        names = {record["name"] for record in records}
        titles = set()
        all_paragraphs = []
        for slug, examples in SLUGS.items():
            with self.subTest(slug=slug):
                doc = (ROOT / "content" / (slug + ".md")).read_text(encoding="utf-8")
                self.assertGreaterEqual(len(doc), 2400)
                title = doc.splitlines()[0]
                self.assertTrue(title.startswith("# "))
                self.assertNotIn(title, titles)
                titles.add(title)
                self.assertNotIn("**", doc)
                self.assertNotIn("직접 사용해 봤", doc)
                self.assertIn("2026년 11월 11일", doc)
                self.assertGreaterEqual(doc.count("## "), 7)
                self.assertIn("|---|---|---|", doc)
                self.assertGreaterEqual(doc.count("- [ ] "), 5)
                self.assertGreaterEqual(doc.count("### "), 3)
                self.assertIn("](/directory)", doc)
                for example in examples:
                    self.assertIn(example, doc)
                    self.assertTrue(any(example in name for name in names))
                paragraphs = [part.strip() for part in doc.split("\n\n") if len(part.strip()) > 80]
                all_paragraphs.extend(p for p in paragraphs if not p.startswith(("링크위키의 등록 설명은", "- [링크위키 주소모음 전체 검색]")))
        self.assertEqual(len(all_paragraphs), len(set(all_paragraphs)))

    def test_no_invented_blog_or_internal_link_destinations(self):
        for slug in SLUGS:
            doc = (ROOT / "content" / (slug + ".md")).read_text(encoding="utf-8")
            for target in re.findall(r"\]\((/[^)]+)\)", doc):
                path = unquote(target.split("?", 1)[0].split("#", 1)[0])
                with self.subTest(slug=slug, target=target):
                    if path in ("/", "/directory", "/categories/"):
                        continue
                    if path.startswith("/categories/"):
                        self.assertTrue((ROOT / (path.lstrip("/") + ".html")).is_file())
                    elif path.startswith("/guides/"):
                        self.assertTrue((ROOT / (path.lstrip("/") + ".html")).is_file())
                    elif path.startswith("/blog/"):
                        self.assertTrue((ROOT / "content" / (path.strip("/").split("/")[-1] + ".md")).is_file())
                    else:
                        self.fail("Unreviewed internal path: " + target)

    def test_build_exposes_all_five_canonicals_and_directory_links(self):
        dist = ROOT / "dist"
        if not (dist / "sitemap.xml").is_file():
            self.skipTest("Build first")
        root = ET.parse(dist / "sitemap.xml").getroot()
        urls = {x.text for x in root.iter() if x.tag.rsplit("}", 1)[-1] == "loc"}
        directory = (dist / "directory.html").read_text(encoding="utf-8")
        self.assertEqual(directory.count('id="site-related-guides"'), 1)
        for slug in SLUGS:
            url = "/blog/" + slug + "/"
            with self.subTest(slug=slug):
                self.assertIn(SITE + url, urls)
                html_path = dist / "blog" / slug / "index.html"
                self.assertTrue(html_path.is_file())
                html = html_path.read_text(encoding="utf-8")
                self.assertIn('href="' + SITE + url + '"', html)
                self.assertIn('<div class="blog-table-scroll"><table>', html)
                self.assertIn('<th scope="col">', html)
                self.assertIn('href="' + url + '"', directory)


if __name__ == "__main__":
    unittest.main()
