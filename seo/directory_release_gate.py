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
              "ai", "search", "sports", "video", "finance", "education",
              "news", "shopping", "travel")


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
        if (tag == "a" and self.inside_card and a.get("href", "").startswith("https://")
                and "directory-source" not in a.get("class", "").split()):
            self.cards[-1]["external_links"] += 1

    def handle_endtag(self, tag):
        if tag == "article":
            self.inside_card = False
        if tag == "div" and self.in_results:
            self.results_depth -= 1
            if self.results_depth == 0:
                self.in_results = False



class CategoryListingParser(HTMLParser):
    """Inspect category cards in the initial HTML, not after browser JavaScript."""
    def __init__(self):
        super().__init__()
        self.cards = []
        self.current = None
        self.canonicals = []
        self.robots = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonicals.append(a.get("href"))
        if tag == "meta" and a.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(a.get("content", "").lower())
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "article" and set(a.get("class", "").split()) & {"item", "v6-card"}:
            self.current = {"names": 0, "external_links": 0}
            self.cards.append(self.current)
        elif self.current and tag in ("strong", "h3"):
            self.current["names"] += 1
        elif (self.current and tag == "a"
              and a.get("href", "").startswith("https://")
              and "directory-source" not in a.get("class", "").split()):
            self.current["external_links"] += 1

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


CATEGORY_LABELS = {
    "community": "커뮤니티", "korean": "한인교민",
    "comics-directory": "만화", "webtoon": "만화·웹툰",
    "ai": "AI 도구", "search": "검색·포털", "sports": "스포츠",
    "video": "영상·OTT", "finance": "금융·경제", "education": "교육·취업",
    "news": "뉴스·언론", "shopping": "쇼핑·가격비교",
    "travel": "생활·교통·여행",
}

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
    evidence_sections = list(re.finditer(
        r'<section\b[^>]*class="[^"]*\bseo-home-evidence\b[^"]*"[^>]*>.*?</section>',
        home_html, re.S,
    ))
    if len(evidence_sections) != 1:
        issues.append("homepage must expose exactly one source-evidence summary")
    else:
        evidence = evidence_sections[0]
        search_form = re.search(
            r'<form\b[^>]*id="lw-home-query"[^>]*>.*?</form>', home_html, re.S
        )
        recent_content = home_html.find('aria-label="최근 등록된 정보"')
        if (not search_form or evidence.start() < search_form.end()
                or (recent_content >= 0 and evidence.start() > recent_content)):
            issues.append("homepage source-evidence summary must follow search and precede recent articles")
        counts = re.search(r'공개 목록\s+(\d+)개\s+가운데\s+(\d+)건', evidence.group(0))
        if not counts or int(counts.group(1)) < 1 or int(counts.group(2)) > int(counts.group(1)):
            issues.append("homepage source-evidence counts are missing or inconsistent")
    if any("noindex" in directive for directive in parser.robots):
        issues.append("directory has noindex")
    if directory_html.count('id="directory-quick-compare"') != 1:
        issues.append("directory quick category comparison missing or duplicated")
    else:
        first = directory_html.index('id="directory-quick-compare"')
        search = directory_html.find('id="v6-form"')
        results = directory_html.find('id="v6-results"')
        if search < 0 or results < 0 or not (search < results < first):
            issues.append("directory results must precede the category comparison")
        section = directory_html[first:directory_html.find("</section>", first)]
        if any('href="/categories/' + slug + '"' not in section for slug in CATEGORIES):
            issues.append("quick category comparison missing category links")
        targets = re.findall(r'href="#(site-[a-f0-9]{14})"', section)
        card_ids = set(re.findall(r'<article\b[^>]*\bid="(site-[a-f0-9]{14})"', directory_html))
        if not targets or any(anchor not in card_ids for anchor in targets):
            issues.append("quick comparison has missing or broken listing anchors")
    if len(parser.cards) != count:
        issues.append(f"static directory cards {len(parser.cards)} != data {count}")
    if any(card["names"] != 1 or card["external_links"] != 1 for card in parser.cards):
        issues.append("directory card missing title or exact external link")
    if any(keyword not in directory_html for keyword in KEYWORDS):
        issues.append("directory intent content is missing a core search term")
    directory_heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", directory_html, re.S)
    if (not directory_heading
            or "사이트모음 전체 목록" not in directory_heading.group(1)
            or "이름·도메인 검색" not in directory_heading.group(1)
            or "이름·도메인" not in directory_heading.group(1)
            or any(keyword in directory_heading.group(1)
                   for keyword in ("주소모음", "링크모음"))):
        issues.append("directory catalog-search heading must use distinct site-list intent")
    home_title = re.search(r"<title>(.*?)</title>", home_html, re.S)
    if not home_title or any(keyword not in home_title.group(1) for keyword in KEYWORDS):
        issues.append("homepage core-keyword title missing")
    directory_title = re.search(r"<title>(.*?)</title>", directory_html, re.S)
    if (not directory_title
            or "사이트모음 전체 목록" not in directory_title.group(1)
            or "검색·비교" not in directory_title.group(1)
            or any(keyword in directory_title.group(1)
                   for keyword in ("주소모음", "링크모음"))):
        issues.append("directory title must use distinct site-list search intent")
    if f"{count}개" not in directory_html.split("</main>", 1)[0]:
        issues.append("directory visible count not derived from verified data")
    if "/directory" not in home.links:
        issues.append("homepage lacks crawlable canonical /directory link")
    if "/categories/" not in home.links:
        issues.append("homepage lacks crawlable category hub link")
    for slug in CATEGORIES:
        if "/categories/" + slug not in home.links:
            issues.append(f"homepage lacks crawlable category link: {slug}")
    for slug in CATEGORIES:
        url = "/categories/" + slug
        if url not in parser.links:
            issues.append(f"directory lacks crawlable category link: {slug}")
        page = category_htmls.get(slug)
        if not page:
            issues.append(f"missing category file: {slug}")
            continue
        cat = CategoryListingParser()
        cat.feed(page)
        if cat.canonicals != [ORIGIN + url]:
            issues.append(f"category canonical mismatch: {slug}")
        if any("noindex" in directive for directive in cat.robots):
            issues.append(f"category has noindex: {slug}")
        expected = sum(1 for item in records
                       if isinstance(item, dict)
                       and item.get("category") == CATEGORY_LABELS[slug])
        if len(cat.cards) != expected:
            issues.append(
                f"static category cards {slug}: {len(cat.cards)} != data {expected}"
            )
        if expected and any(
            card["names"] != 1 or card["external_links"] != 1
            for card in cat.cards
        ):
            issues.append(f"category card missing title or exact external link: {slug}")
        if "/directory" not in cat.links or "/categories/" not in cat.links:
            issues.append(f"category lacks crawlable directory navigation: {slug}")
    # SiteMap must actually include the canonical, not a .html redirect.
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(sitemap_xml)
        urls = {e.text for e in root.iter() if e.tag.endswith("}loc")}
        for url in (ORIGIN + "/", ORIGIN + "/directory", ORIGIN + "/categories/"):
            if url not in urls:
                issues.append(f"sitemap missing: {url}")
        for slug in CATEGORIES:
            url = ORIGIN + "/categories/" + slug
            if url not in urls:
                issues.append(f"sitemap missing category: {url}")
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
    print(f"PASS: {count} crawlable directory cards, {len(CATEGORIES)} statically populated category paths, core intents and canonical sitemap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
