#!/usr/bin/env python3
"""Compare deployed public SEO pages with the exact generated release.

This is a public, read-only deployment smoke check, not an index-status or
ranking claim. External full-service destination is never contacted here.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

SITE = "https://linkwiki.info"
CORE = ("주소모음", "링크모음", "사이트모음")
CATEGORY_PATHS = (
    "/categories/community", "/categories/korean",
    "/categories/comics-directory", "/categories/webtoon",
    "/categories/ai", "/categories/search",
    "/categories/sports", "/categories/video",
)


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.in_h1 = False
        self.title = []
        self.headings = []
        self.canonicals = []
        self.descriptions = []
        self.noindex = False
        self.links = set()
        self.ids = set()

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.in_h1 = True
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.descriptions.append(attrs.get("content", ""))
        if tag == "meta" and attrs.get("name", "").lower() in ("robots", "googlebot"):
            self.noindex |= bool(re.search(r"(?:^|[\s,])(?:noindex|none)(?:$|[\s,])",
                                           attrs.get("content", "").lower()))
        if tag == "a":
            self.links.add(attrs.get("href", ""))
        if attrs.get("id"):
            self.ids.add(attrs["id"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "h1":
            self.in_h1 = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.in_h1:
            self.headings.append(data)


def parse_page(text):
    parser = PageMetadata()
    parser.feed(text)
    return parser


class VisibleSiteCountParser(HTMLParser):
    """Extract text visible to search crawlers, excluding script and styles."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.body_depth = 0
        self.skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.body_depth += 1
        elif tag in ("script", "style", "template", "noscript"):
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "body":
            self.body_depth = max(0, self.body_depth - 1)
        elif tag in ("script", "style", "template", "noscript"):
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if self.body_depth and not self.skip_depth:
            self.parts.append(data)


def visible_site_counts(html):
    """Return observed directory sizes in page text, not JS or SEO tags."""
    parser = VisibleSiteCountParser()
    parser.feed(html)
    body = " ".join(parser.parts)
    patterns = (
        r"(?<!\d)(\d{2,5})\s*개\s*(?:등록\s*)?(?:사이트|항목)",
        r"등록(?:된)?\s*(?:사이트|항목)\s*(\d{2,5})\s*개",
    )
    return sorted(int(value) for pattern in patterns
                  for value in re.findall(pattern, body))


def release_content_sections(html, path):
    """Extract deterministic substantive SEO sections from generated HTML."""
    patterns = {
        "/": (
            r'<section class="wrap seo-directory-examples"[^>]*>.*?</section>',
        ),
        "/directory": (
            r'<section\b(?=[^>]*\bclass="[^"]*\bseo-search-help\b)[^>]*>.*?</section>',
            r'<section class="seo-directory-category">.*?</section>',
            r'<section\b(?=[^>]*\bclass="[^"]*\bseo-purpose-comparison\b)[^>]*>.*?</section>',
            r'<section\b(?=[^>]*\bclass="[^"]*\bseo-directory-guides\b)[^>]*>.*?</section>',
        ),
        "/categories/": (
            r'<article class="v6-card">.*?</article>',
        ),
    }
    if path in CATEGORY_PATHS:
        patterns[path] = (
            r'<section\b(?=[^>]*\bclass="[^"]*\bseo-category-decision\b)[^>]*>.*?</section>',
            r'<article class="v6-card">.*?</article>',
            # Category listing pages use the "item" card variant.
            # Compare real rendered entries so an old 36-site category
            # cannot pass after the published directory grows to 44.
            r'<article\b(?=[^>]*\bclass="[^"]*\bitem\b)[^>]*>.*?</article>',
        )
    # The Korean search category contains an original official-service
    # comparison in addition to its generic category cards. Verify the
    # substantive guidance deploys with the exact checked-out build.
    if path == "/categories/search":
        patterns[path] += (
            r'<section class="wrap" aria-label="국내 생활 민원과 공공자료 찾기">.*?</section>',
            r'<section class="wrap" aria-label="창업·특허·기업지원 공식 사이트 비교">.*?</section>',
        )
    blocks = []
    for expression in patterns.get(path, ()):
        blocks.extend(re.findall(expression, html, flags=re.S))
    return blocks


class DirectoryCardParser(HTMLParser):
    """Extract visible site cards without depending on whitespace or attributes."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self.card = None
        self.field = None

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == "article" and "v6-card" in attrs.get("class", "").split():
            self.card = {"name": "", "category": "", "description": "",
                         "domain": "", "url": ""}
            return
        if self.card is None:
            return
        self.field = {"h3": "name", "small": "category", "p": "description"}.get(tag)
        if tag == "span" and "site-domain" in attrs.get("class", "").split():
            self.field = "domain"
        if tag == "a" and str(attrs.get("href", "")).startswith("https://"):
            self.card["url"] = attrs["href"]

    def handle_data(self, text):
        if self.card is not None and self.field:
            self.card[self.field] += text

    def handle_endtag(self, tag):
        if self.card is None:
            return
        if tag == "article":
            self.cards.append(tuple(self.card[field].strip() for field in
                                    ("name", "category", "description", "domain", "url")))
            self.card = None
            self.field = None
        elif tag in ("h3", "small", "p", "span"):
            self.field = None


def directory_cards(html):
    parser = DirectoryCardParser()
    parser.feed(html)
    return parser.cards


def check_core_sitemap_lastmod(expected_xml, live_xml):
    """Compare recorded meaningful modification dates, never the CI run date."""
    try:
        expected_root = ET.fromstring(expected_xml)
        live_root = ET.fromstring(live_xml)
    except ET.ParseError as exc:
        return ["sitemap lastmod comparison XML invalid: " + str(exc)]
    def values(root):
        found = {}
        for item in root:
            loc, lastmod = None, None
            for child in item:
                if child.tag.endswith("}loc") or child.tag == "loc":
                    loc = child.text
                if child.tag.endswith("}lastmod") or child.tag == "lastmod":
                    lastmod = child.text
            if loc:
                found[loc] = lastmod
        return found
    expected, live = values(expected_root), values(live_root)
    problems = []
    for path in ("/", "/directory", "/categories/") + CATEGORY_PATHS:
        url = SITE + path
        recorded = expected.get(url)
        if recorded and live.get(url) != recorded:
            problems.append(f"sitemap.xml: deployed lastmod for {path} differs from generated build "
                            f"({live.get(url) or 'missing'} != {recorded})")
    return problems


def check_page(expected_html, live_html, path):
    """Report semantic and functionality drift between live and build."""
    expected, live = parse_page(expected_html), parse_page(live_html)
    errors = []
    if "".join(expected.title).strip() != "".join(live.title).strip():
        errors.append(f"{path}: deployed title differs from generated build")
    if expected.descriptions != live.descriptions:
        errors.append(f"{path}: deployed meta description differs from generated build")
    if path in ("/", "/directory"):
        expected_counts = visible_site_counts(expected_html)
        live_counts = visible_site_counts(live_html)
        if expected_counts and expected_counts != live_counts:
            errors.append(
                f"{path}: deployed visible site counts differ from generated build "
                f"({live_counts} != {expected_counts})")
    if ["".join(expected.headings).strip()] != ["".join(live.headings).strip()]:
        errors.append(f"{path}: deployed H1 differs from generated build")
    if live.canonicals != [SITE + path]:
        errors.append(f"{path}: deployed canonical differs or is duplicated")
    if live.noindex:
        errors.append(f"{path}: deployed robots noindex detected")
    # Title/H1 can match while Cloudflare still serves stale SEO list content.
    # Compare deterministic, data-backed visible sections as well.
    expected_sections = release_content_sections(expected_html, path)
    live_sections = release_content_sections(live_html, path)
    if expected_sections and expected_sections != live_sections:
        errors.append(f"{path}: deployed directory examples differ from current build")
    if path == "/":
        if '<form action="/directory" class="lw-search"' not in live_html:
            errors.append("/: homepage site search does not target canonical /directory")
        if "주소모음 링크모음 사이트모음 이용 안내" not in live_html:
            errors.append("/: core keyword search-intent section missing on live site")
        if "/directory" not in live.links or "/categories/" not in live.links:
            errors.append("/: links to primary directory and category hub missing")
    if path == "/categories/":
        for link in CATEGORY_PATHS:
            if link not in live.links:
                errors.append(f"/categories/: missing category link {link}")
    if path == "/directory":
        expected_cards = directory_cards(expected_html)
        live_cards = directory_cards(live_html)
        if expected_cards and expected_cards != live_cards:
            errors.append(f"/directory: deployed site cards differ from generated build "
                          f"({len(live_cards)} vs {len(expected_cards)} cards)")
        if not all(keyword in "".join(live.headings) for keyword in CORE):
            errors.append("/directory: three primary keywords missing from visible H1")
        if "v6-results" not in live.ids or "v6-query" not in live.ids:
            errors.append("/directory: working search UI anchors missing")
        if "directory-category-schema" not in live.ids:
            errors.append("/directory: category structured-data marker not deployed")
        for link in CATEGORY_PATHS:
            if link not in live.links:
                errors.append(f"/directory: missing crawlable category link {link}")
    return errors


def check_sitemap(text):
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        return [f"sitemap XML invalid: {error}"]
    urls = {el.text for el in root.iter() if el.tag.endswith("}loc") and el.text}
    required = {SITE + "/", SITE + "/directory", SITE + "/categories/"}
    required.update(SITE + path for path in CATEGORY_PATHS)
    return [f"sitemap missing {url}" for url in sorted(required - urls)]


def google_index_blocked_by_header(header_values):
    """Detect generic/Googlebot noindex headers; ignore other crawler rules."""
    for header in header_values:
        for directive in str(header).split(","):
            part = directive.strip().lower()
            if ":" in part:
                agent, rule = part.split(":", 1)
                if agent.strip() != "googlebot":
                    continue
                part = rule.strip()
            if re.search(r"(?:^|[\s;,])(?:noindex|none)(?:$|[\s;,])", part):
                return True
    return False


def fetch_public(path):
    url = SITE + path
    request = Request(url, headers={"User-Agent": "LinkWiki-ReleaseQA/1.0"})
    with urlopen(request, timeout=25) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != "linkwiki.info":
            raise RuntimeError("Unexpected cross-origin or insecure redirect: " + url)
        # A 200 response reached through /directory.html or another URL is
        # not proof the extensionless canonical was served directly. Such
        # redirects can leave Google inspecting a different URL variant.
        if path in ("/", "/directory", "/categories/") + CATEGORY_PATHS:
            if final.path != path or final.query or final.fragment:
                raise RuntimeError("Canonical URL redirected or gained query parameters: "
                                   + url + " -> " + response.geturl())
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        if path in ("/", "/directory", "/categories/") + CATEGORY_PATHS:
            tags = response.headers.get_all("X-Robots-Tag", [])
            if google_index_blocked_by_header(tags):
                raise RuntimeError("HTTP X-Robots-Tag prohibits Google indexing: " + url)
        return response.read().decode("utf-8", errors="replace")


def extract_directory_sites(script):
    """Read the public search dataset without evaluating JavaScript."""
    match = re.search(r"const sites=(\[.*?\]);\s*\(\(\)=>", script, re.S)
    if match is None:
        raise ValueError("directory JavaScript site dataset missing")
    records = json.loads(match.group(1))
    if not isinstance(records, list):
        raise ValueError("directory JavaScript site dataset is not a list")
    return records


def run(dist, fetch=fetch_public):
    expected_map = {"/": dist / "index.html",
                    "/directory": dist / "directory.html",
                    "/categories/": dist / "categories" / "index.html"}
    expected_map.update({
        path: dist / "categories" / (path.rsplit("/", 1)[-1] + ".html")
        for path in CATEGORY_PATHS
    })
    problems = []
    for path, source in expected_map.items():
        expected = source.read_text(encoding="utf-8")
        try:
            live = fetch(path)
            problems.extend(check_page(expected, live, path))
        except (OSError, RuntimeError, ValueError) as error:
            problems.append(f"{path}: fetch failed: {error}")
    try:
        sitemap = fetch("/sitemap.xml")
        problems.extend(check_sitemap(sitemap))
        expected_sitemap = (dist / "sitemap.xml")
        if expected_sitemap.is_file():
            problems.extend(check_core_sitemap_lastmod(
                expected_sitemap.read_text(encoding="utf-8"), sitemap))
    except (OSError, RuntimeError, ValueError) as error:
        problems.append(f"/sitemap.xml: fetch failed: {error}")
    try:
        live_search = fetch("/assets/directory-search.js")
        if "terms.every(term => haystack.includes(term))" not in live_search or "function sortResults(" not in live_search:
            problems.append("/assets/directory-search.js: multi-term search not deployed")
        live_script = fetch("/assets/directory.js")
        if "window.LinkWikiSearch.sortResults" not in live_script:
            problems.append("/assets/directory.js: relevance search integration not deployed")
        # A previous 188-site search bundle must not pass after 192 cards
        # deploy. Compare the exact data, not just the presence of search code.
        expected_script = dist / "assets" / "directory.js"
        if expected_script.is_file():
            source_sites = extract_directory_sites(expected_script.read_text(encoding="utf-8"))
            try:
                deployed_sites = extract_directory_sites(live_script)
                if deployed_sites != source_sites:
                    problems.append("/assets/directory.js: deployed search dataset differs from release "
                                    f"({len(deployed_sites)} vs {len(source_sites)} records)")
            except ValueError as error:
                problems.append(f"/assets/directory.js: invalid deployed site data: {error}")
    except (OSError, RuntimeError, ValueError) as error:
        problems.append(f"/assets/directory.js: fetch failed: {error}")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    args = parser.parse_args()
    if not args.dist.is_dir():
        parser.error("build output missing: run python3 build.py first")
    errors = run(args.dist)
    for error in errors:
        print("FAIL:", error)
    if errors:
        print(f"Public release verification FAILED ({len(errors)} issues)")
        return 1
    print("PASS: live home, directory, categories and search script match key release checks")
    print("This checks deployment parity, not Google indexing or search ranking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
