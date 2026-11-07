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


def check_page(expected_html, live_html, path):
    """Report semantic and functionality drift between live and build."""
    expected, live = parse_page(expected_html), parse_page(live_html)
    errors = []
    if "".join(expected.title).strip() != "".join(live.title).strip():
        errors.append(f"{path}: deployed title differs from generated build")
    if ["".join(expected.headings).strip()] != ["".join(live.headings).strip()]:
        errors.append(f"{path}: deployed H1 differs from generated build")
    if live.canonicals != [SITE + path]:
        errors.append(f"{path}: deployed canonical differs or is duplicated")
    if live.noindex:
        errors.append(f"{path}: deployed robots noindex detected")
    if path == "/":
        if "주소모음 링크모음 사이트모음 이용 안내" not in live_html:
            errors.append("/: core keyword search-intent section missing on live site")
        if "/directory" not in live.links or "/categories/" not in live.links:
            errors.append("/: links to primary directory and category hub missing")
    if path == "/directory":
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


def fetch_public(path):
    url = SITE + path
    request = Request(url, headers={"User-Agent": "LinkWiki-ReleaseQA/1.0"})
    with urlopen(request, timeout=25) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != "linkwiki.info":
            raise RuntimeError("Unexpected cross-origin or insecure redirect: " + url)
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8", errors="replace")


def run(dist, fetch=fetch_public):
    expected_map = {"/": dist / "index.html",
                    "/directory": dist / "directory.html"}
    problems = []
    for path, source in expected_map.items():
        expected = source.read_text(encoding="utf-8")
        try:
            live = fetch(path)
            problems.extend(check_page(expected, live, path))
        except (OSError, RuntimeError, ValueError) as error:
            problems.append(f"{path}: fetch failed: {error}")
    try:
        problems.extend(check_sitemap(fetch("/sitemap.xml")))
    except (OSError, RuntimeError, ValueError) as error:
        problems.append(f"/sitemap.xml: fetch failed: {error}")
    try:
        live_script = fetch("/assets/directory.js")
        if "const lookup=coreIntent?'':q" not in live_script:
            problems.append("/assets/directory.js: core query behavior not deployed")
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
