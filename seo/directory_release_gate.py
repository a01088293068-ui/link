#!/usr/bin/env python3
"""Fail closed when a LinkWiki SEO release loses crawlable directory content.

No network, GSC access, indexing request, credential, or claim about Google rank.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://linkwiki.info"
KEYWORDS = ("주소모음", "링크모음", "사이트모음")
CATEGORIES = ("community", "korean", "comics-directory", "webtoon",
              "ai", "search", "sports", "video")


class VisibleDirectoryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.links = []
        self.canonicals = []
        self.robots = []
        self.in_results = False
        self.results_depth = 0
        self.inside_card = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonicals.append(a.get("href"))
        if tag == "meta" and a.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(a.get("content", "").lower())
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "div":
            if a.get("id") == "v6-results":
                self.in_results = True
                self.results_depth = 1
            elif self.in_results:
                self.results_depth += 1
        if tag == "article" and self.in_results and "v6-card" in a.get("class", "").split():
            self.cards.append({"names": 0, "external_links": 0})
            self.inside_card = True
        if tag == "h3" and self.inside_card:
            self.cards[-1]["names"] += 1
        if tag == "a" and self.inside_card and a.get("href", "").startswith("https://"):
            self.cards[-1]["external_links"] += 1

    def handle_endtag(self, tag):
        if tag == "article":
            self.inside_card = False
        if tag == "div" and self.in_results:
            self.results_depth -= 1
            if self.results_depth == 0:
                self.in_results = False


def validate(directory_html, home_html, records, category_htmls, sitemap_xml):
    """Return concrete failure reasons, never infer Google's indexed status."""
    issues = []
    if not isinstance(records, list) or not records:
        return ["verified directory data empty"]
    count = len(records)
    parser = VisibleDirectoryParser()
    parser.feed(directory_html)
    home = VisibleDirectoryParser()
    home.feed(home_html)
    if parser.canonicals != [ORIGIN + "/directory"]:
        issues.append("directory canonical missing or noncanonical")
    if home.canonicals != [ORIGIN + "/"]:
        issues.append("homepage canonical missing or noncanonical")
    if any("noindex" in directive for directive in parser.robots):
        issues.append("directory has noindex")
    if directory_html.count('id="directory-quick-compare"') != 1:
        issues.append("directory quick category comparison missing or duplicated")
    else:
        first = directory_html.index('id="directory-quick-compare"')
        search = directory_html.find('id="v6-form"')
        results = directory_html.find('id="v6-results"')
        if search < 0 or results < 0 or not (search < first < results):
            issues.append("directory category comparison not adjacent to search")
        section = directory_html[first:directory_html.find("</section>", first)]
        if any('href="/categories/' + slug + '"' not in section for slug in CATEGORIES):
            issues.append("quick category comparison missing category links")
        targets = re.findall(r'href="#(site-[a-f0-9]{14})"', section)
        card_ids = set(re.findall(r'<article\\b[^>]*\\bid="(site-[a-f0-9]{14})"', directory_html))
        if not targets or any(anchor not in card_ids for anchor in targets):
            issues.append("quick comparison has missing or broken listing anchors")
    if len(parser.cards) != count:
        issues.append(f"static directory cards {len(parser.cards)} != data {count}")
    if any(card["names"] != 1 or card["external_links"] != 1 for card in parser.cards):
        issues.append("directory card missing title or exact external link")
    for keyword in KEYWORDS:
        if keyword not in directory_html.split("</h1>", 1)[0]:
            issues.append(f"directory primary heading missing {keyword}")
        if keyword not in home_html.split("</title>", 1)[0]:
            issues.append(f"homepage title missing {keyword}")
    if f"{count}개" not in directory_html.split("</main>", 1)[0]:
        issues.append("directory visible count not derived from verified data")
    if "/directory" not in home.links:
        issues.append("homepage lacks crawlable canonical /directory link")
    for slug in CATEGORIES:
        url = "/categories/" + slug
        if url not in parser.links:
            issues.append(f"directory lacks crawlable category link: {slug}")
        page = category_htmls.get(slug)
        if not page:
            issues.append(f"missing category file: {slug}")
            continue
        cat = VisibleDirectoryParser()
        cat.feed(page)
        if cat.canonicals != [ORIGIN + url]:
            issues.append(f"category canonical mismatch: {slug}")
    # SiteMap must actually include the canonical, not a .html redirect.
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(sitemap_xml)
        urls = {e.text for e in root.iter() if e.tag.endswith("}loc")}
        for url in (ORIGIN + "/", ORIGIN + "/directory", ORIGIN + "/categories/"):
            if url not in urls:
                issues.append(f"sitemap missing: {url}")
    except Exception:
        issues.append("invalid sitemap XML")
    return issues


def main():
    dist = ROOT / "dist"
    if not (dist / "directory.html").is_file():
        print("Release not built: python3 build.py first", file=sys.stderr)
        return 2
    issues = validate(
        (dist / "directory.html").read_text(encoding="utf-8"),
        (dist / "index.html").read_text(encoding="utf-8"),
        json.loads((dist / "assets" / "verified-directory.json").read_text(encoding="utf-8")),
        {slug: (dist / "categories" / f"{slug}.html").read_text(encoding="utf-8")
         if (dist / "categories" / f"{slug}.html").exists() else ""
         for slug in CATEGORIES},
        (dist / "sitemap.xml").read_text(encoding="utf-8"),
    )
    if issues:
        for issue in issues:
            print("FAIL:", issue)
        return 1
    count = len(json.loads((dist / "assets" / "verified-directory.json").read_text(encoding="utf-8")))
    print(f"PASS: {count} crawlable directory cards, 8 category paths, core intents and canonical sitemap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
