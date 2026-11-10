#!/usr/bin/env python3
"""Compare live release against built output; not a Google rank/index check."""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree

BASE = "https://linkwiki.info"

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = {"title": [], "h1": []}
        self.active = None
        self.canonical = []
        self.robots = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.parts: self.active = tag
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonical.append(a.get("href", ""))
        if tag == "meta" and a.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(a.get("content", ""))
    def handle_endtag(self, tag):
        if tag == self.active: self.active = None
    def handle_data(self, data):
        if self.active: self.parts[self.active].append(data)
    def value(self, tag):
        return "".join(self.parts[tag]).strip()

def fetch(path):
    req = Request(BASE + path, headers={"User-Agent": "LinkWikiReleaseCheck/1.0"})
    with urlopen(req, timeout=20) as res:
        body = res.read(2_000_001)
        if len(body) > 2_000_000: raise ValueError("response too large")
        return res.status, res.geturl(), body.decode("utf-8", "replace"), res.headers

def check(source_html, load=fetch):
    errors, observations = [], []
    source = Page()
    source.feed(source_html)
    for path in ("/", "/directory"):
        try:
            status, final, body, headers = load(path)
            page = Page()
            page.feed(body)
            observations.append(f"{path}: HTTP {status} -> {final}")
            if status != 200 or final != BASE + path:
                errors.append(f"{path}: noncanonical status/redirect")
            if page.canonical != [BASE + path]:
                errors.append(f"{path}: canonical mismatch")
            if any(re.search(r"\bnoindex\b", x, re.I) for x in page.robots):
                errors.append(f"{path}: HTML noindex")
            if re.search(r"\bnoindex\b", str(headers.get("X-Robots-Tag", "")), re.I):
                errors.append(f"{path}: HTTP noindex")
            if path == "/":
                for tag in ("title", "h1"):
                    if source.value(tag) != page.value(tag):
                        errors.append(f"/: live {tag} differs from repository")
                    for keyword in ("주소모음", "링크모음", "사이트모음"):
                        if keyword not in page.value(tag):
                            errors.append(f"/: {tag} missing {keyword}")
        except Exception as exc:
            errors.append(f"{path}: fetch error ({type(exc).__name__}: {exc})")
    try:
        status, final, body, _ = load("/sitemap.xml")
        root = ElementTree.fromstring(body)
        urls = [e.text for e in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        observations.append(f"/sitemap.xml: HTTP {status}; {len(urls)} URLs")
        if status != 200 or final != BASE + "/sitemap.xml":
            errors.append("/sitemap.xml: status/redirect")
        for path in ("/", "/directory"):
            if BASE + path not in urls: errors.append(f"sitemap missing {path}")
    except Exception as exc:
        errors.append(f"sitemap fetch/parse error ({type(exc).__name__}: {exc})")
    return errors, observations

def main():
    source = Path("dist/index.html").read_text(encoding="utf-8")
    errors, observations = check(source)
    print("# Public release consistency (NOT Google indexing or search rankings)")
    for line in observations: print("- " + line)
    print(f"Result: {'FAIL' if errors else 'PASS'} ({len(errors)} issues)")
    for line in errors: print("- " + line)
    return int(bool(errors))

if __name__ == "__main__":
    sys.exit(main())
