#!/usr/bin/env python3
"""Compare live release against built output; not a Google rank/index check."""
import hashlib
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

def related_targets(html):
    """Extract the hrefs in the generated, visitor-visible related guides block."""
    match = re.search(
        r'<section\b[^>]*class="blog-related"[^>]*>.*?</section>',
        html, re.S | re.I,
    )
    if not match:
        return set()
    return set(re.findall(r'<a\b[^>]*href="([^"]+)"', match.group(), re.I))


def directory_cards(html):
    """Read actual server-rendered HTML cards, never JS-only listings."""
    from html import unescape
    container = re.search(
        r'<div\b[^>]*\bid="v6-results"[^>]*>(.*?)</div>', html,
        re.I | re.S,
    )
    if not container:
        return []
    cards = []
    for match in re.finditer(
        r'<article\b[^>]*class="v6-card"[^>]*>(.*?)</article>',
        container.group(1), re.I | re.S,
    ):
        fragment = match.group(1)
        parts = [
            re.search(r'<small>(.*?)</small>', fragment, re.I | re.S),
            re.search(r'<h3>(.*?)</h3>', fragment, re.I | re.S),
            re.search(r'<a\b[^>]*\bhref="([^"]+)"', fragment, re.I | re.S),
            re.search(r'<p>(.*?)</p>', fragment, re.I | re.S),
        ]
        if any(piece is None for piece in parts):
            return []
        cards.append(tuple(unescape(piece.group(1)).strip() for piece in parts))
    return cards


def directory_script_versions(html):
    """Capture URL fingerprints for the four browser files used by the directory."""
    names = ("directory-search.js", "directory.js", "mobile-menu.js",
             "address-inspector.js")
    versions = {}
    for name in names:
        match = re.findall(
            r'<script\b[^>]*\bsrc="(?:/)?assets/' + re.escape(name) +
            r'\?v=([a-f0-9]{12})"[^>]*>', html, re.I,
        )
        if len(match) == 1:
            versions[name] = match[0]
    return versions


def maintenance_signature(html):
    """Extract the published total and category counts from the maintenance guide."""
    total = re.search(r'공개 목록에는 현재\s*(\d+)개 사이트', html)
    rows = re.findall(
        r'<tr>\s*<th><a href="/categories/([^"]+)">.*?</a></th>'
        r'\s*<td>(\d+)개</td><td>([^<]*)</td>\s*</tr>',
        html, re.S,
    )
    return (int(total.group(1)) if total else None, tuple(rows))

def category_hub_signature(html):
    """Extract the overall directory size and data-backed category-card counts."""
    total = re.search(
        r'<a href="/directory">(\d+)개 사이트 이름·도메인 전체 검색</a>', html
    )
    rows = re.findall(
        r'<article class="v6-card">.*?<a href="/categories/([^"]+)">.*?</a>'
        r'.*?<p>(\d+)개 등록 사이트</p>.*?</article>',
        html, re.S,
    )
    return (int(total.group(1)) if total else None,
            tuple((slug, int(count)) for slug, count in rows))



def homepage_evidence_signature(html):
    """Read the homepage's public source-evidence disclosure and destination."""
    section = re.search(
        r'<section\b(?=[^>]*\bclass="[^"]*\bseo-home-evidence\b)[^>]*>(.*?)</section>',
        html, re.S | re.I,
    )
    if not section:
        return None
    count = re.search(r'(\d+)건의 출처 대조 기록', section.group(1))
    target = re.search(r'<a\b[^>]*href="([^"]+)"[^>]*>대조한 출처와 확인일 보기</a>', section.group(1))
    if not count or not target:
        return None
    return int(count.group(1)), target.group(1)

def check(source_html, load=fetch, article_sources=None, directory_source=None, script_source=None, category_sources=None, maintenance_source=None, category_hub_source=None):
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
            if path == "/directory" and directory_source is not None:
                source_cards = directory_cards(directory_source)
                live_cards = directory_cards(body)
                observations.append(
                    f"/directory: built {len(source_cards)} static cards; "
                    f"live {len(live_cards)} static cards")
                if len(source_cards) < 200:
                    errors.append("/directory: generated static card coverage unexpectedly low")
                if source_cards != live_cards:
                    errors.append("/directory: live static listings differ from built directory")
                built_versions = directory_script_versions(directory_source)
                live_versions = directory_script_versions(body)
                observations.append(
                    f"/directory: {len(live_versions)}/4 fingerprinted browser scripts")
                if len(built_versions) != 4:
                    errors.append("/directory: generated asset fingerprints incomplete")
                if live_versions != built_versions:
                    errors.append("/directory: live browser asset versions differ from built output")
                expected_head = Page()
                expected_head.feed(directory_source)
                for tag in ("title", "h1"):
                    if expected_head.value(tag) != page.value(tag):
                        errors.append(f"/directory: live {tag} differs from built output")
            if path == "/":
                for tag in ("title", "h1"):
                    if source.value(tag) != page.value(tag):
                        errors.append(f"/: live {tag} differs from built output")
                # The homepage serves the address-finding intent. Other
                # primary intents have their own landing pages; requiring all
                # three phrases in this title both duplicates intent and
                # contradicts the published page strategy.
                for keyword in ("주소모음",):
                    if keyword not in page.value("title"):
                        errors.append(f"/: title missing {keyword}")
                expected_evidence = homepage_evidence_signature(source_html)
                if expected_evidence is not None:
                    live_evidence = homepage_evidence_signature(body)
                    observations.append(
                        f"/: built homepage source-evidence {expected_evidence[0]} records; "
                        f"live {live_evidence[0] if live_evidence else 'missing'}")
                    if live_evidence != expected_evidence:
                        errors.append("/: live homepage source-evidence disclosure differs from build")
        except Exception as exc:
            errors.append(f"{path}: fetch error ({type(exc).__name__}: {exc})")
    if script_source is not None:
        try:
            status, final, body, headers = load("/assets/directory.js")
            expected_hash = hashlib.sha256(script_source.encode("utf-8")).hexdigest()[:12]
            live_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
            observations.append(
                f"/assets/directory.js: HTTP {status}; "
                f"built={expected_hash}; live={live_hash}")
            if status != 200 or final != BASE + "/assets/directory.js":
                errors.append("/assets/directory.js: noncanonical status/redirect")
            if script_source != body:
                errors.append("/assets/directory.js: live search code differs from built output")
            if "querySelectorAll('article.v6-card')" not in body:
                errors.append("/assets/directory.js: static-card search wiring absent")
            if re.search(r"const\s+sites\s*=\s*\[", body):
                errors.append("/assets/directory.js: duplicate site catalog reintroduced")
        except Exception as exc:
            errors.append(f"/assets/directory.js: fetch error ({type(exc).__name__}: {exc})")

    # Ensure published guide pages contain the links generated by this build.
    # Sampling is bounded, so the audit stays lightweight.
    for path, expected_html in (article_sources or {}).items():
        if not re.fullmatch(r"/blog/[a-zA-Z0-9_-]+/", path):
            errors.append(f"invalid article audit path: {path}")
            continue
        expected = Page()
        expected.feed(expected_html)
        targets = related_targets(expected_html)
        if not targets:
            continue
        try:
            status, final, body, headers = load(path)
            actual = Page()
            actual.feed(body)
            observations.append(f"{path}: HTTP {status}; {len(related_targets(body))} related links")
            if status != 200 or final != BASE + path:
                errors.append(f"{path}: article status/redirect")
            if actual.canonical != [BASE + path]:
                errors.append(f"{path}: article canonical mismatch")
            if expected.value("h1") != actual.value("h1"):
                errors.append(f"{path}: article heading differs from built output")
            if any(re.search(r"\bnoindex\b", x, re.I) for x in actual.robots):
                errors.append(f"{path}: article HTML noindex")
            if re.search(r"\bnoindex\b", str(headers.get("X-Robots-Tag", "")), re.I):
                errors.append(f"{path}: article HTTP noindex")
            missing = targets - related_targets(body)
            if missing:
                errors.append(f"{path}: missing deployed related links: {', '.join(sorted(missing))}")
        except Exception as exc:
            errors.append(f"{path}: article fetch error ({type(exc).__name__}: {exc})")

    # Category landing pages must expose the matching editorial guide in
    # deployed HTML, not merely in the build artifact or after JS runs.
    for path, expected_html in (category_sources or {}).items():
        try:
            status, final, body, headers = load(path)
            observations.append(f"{path}: HTTP {status} -> {final}")
            expected_links = set(re.findall(
                r'<a\b[^>]*href="(/blog/[^"]+)"', expected_html, re.I
            ))
            deployed_links = set(re.findall(
                r'<a\b[^>]*href="([^"]+)"', body, re.I
            ))
            if status != 200 or final != BASE + path:
                errors.append(f"{path}: noncanonical status/redirect")
            if not expected_links.issubset(deployed_links):
                errors.append(f"{path}: missing deployed editorial guide links")
        except Exception as exc:
            errors.append(f"{path}: fetch failed ({type(exc).__name__}: {exc})")

    # The category hub is a primary crawlable entry point. Verify its
    # overall total and every category count against the same generated build.
    if category_hub_source is not None:
        path = "/categories/"
        try:
            status, final, body, headers = load(path)
            expected = Page()
            expected.feed(category_hub_source)
            actual = Page()
            actual.feed(body)
            expected_signature = category_hub_signature(category_hub_source)
            actual_signature = category_hub_signature(body)
            observations.append(
                f"{path}: built {expected_signature[0]} sites / "
                f"{len(expected_signature[1])} category rows; live "
                f"{actual_signature[0]} sites / {len(actual_signature[1])} category rows")
            if status != 200 or final != BASE + path:
                errors.append(f"{path}: noncanonical status/redirect")
            if actual.canonical != [BASE + path]:
                errors.append(f"{path}: canonical mismatch")
            if expected.value("h1") != actual.value("h1"):
                errors.append(f"{path}: live heading differs from built output")
            if expected_signature[0] is None or len(expected_signature[1]) != 13:
                errors.append(f"{path}: generated category hub counts missing or incomplete")
            if actual_signature != expected_signature:
                errors.append(f"{path}: live category hub totals/category counts differ from build")
            if any(re.search(r"\bnoindex\b", x, re.I) for x in actual.robots):
                errors.append(f"{path}: HTML noindex")
            if re.search(r"\bnoindex\b", str(headers.get("X-Robots-Tag", "")), re.I):
                errors.append(f"{path}: HTTP noindex")
        except Exception as exc:
            errors.append(f"{path}: fetch error ({type(exc).__name__}: {exc})")

    # The maintenance guide must be built from the same live catalogue as
    # the homepage and directory. A stale count here undermines the public
    # evidence trail even when the main directory itself is current.
    if maintenance_source is not None:
        path = "/guides/directory-maintenance"
        try:
            status, final, body, headers = load(path)
            expected = Page()
            expected.feed(maintenance_source)
            actual = Page()
            actual.feed(body)
            expected_signature = maintenance_signature(maintenance_source)
            actual_signature = maintenance_signature(body)
            observations.append(
                f"{path}: built {expected_signature[0]} sites / "
                f"{len(expected_signature[1])} category rows; live "
                f"{actual_signature[0]} sites / {len(actual_signature[1])} category rows")
            if status != 200 or final != BASE + path:
                errors.append(f"{path}: noncanonical status/redirect")
            if actual.canonical != [BASE + path]:
                errors.append(f"{path}: canonical mismatch")
            if expected.value("h1") != actual.value("h1"):
                errors.append(f"{path}: live heading differs from built output")
            if expected_signature[0] is None or not expected_signature[1]:
                errors.append(f"{path}: generated catalogue counts missing")
            if actual_signature != expected_signature:
                errors.append(f"{path}: live catalogue totals/category counts differ from build")
            if any(re.search(r"\bnoindex\b", x, re.I) for x in actual.robots):
                errors.append(f"{path}: HTML noindex")
            if re.search(r"\bnoindex\b", str(headers.get("X-Robots-Tag", "")), re.I):
                errors.append(f"{path}: HTTP noindex")
        except Exception as exc:
            errors.append(f"{path}: fetch error ({type(exc).__name__}: {exc})")

    try:
        status, final, body, _ = load("/robots.txt")
        observations.append(f"/robots.txt: HTTP {status} -> {final}")
        if status != 200 or final != BASE + "/robots.txt":
            errors.append("/robots.txt: status/redirect")
        lines = [line.split("#", 1)[0].strip() for line in body.splitlines()]
        sitemap_lines = [line.partition(":")[2].strip() for line in lines
                         if line.lower().startswith("sitemap:")]
        if BASE + "/sitemap.xml" not in sitemap_lines:
            errors.append("/robots.txt: canonical sitemap reference missing")
        # Googlebot can be blocked in its own group even if wildcard allows all.
        groups, current_agents, current_rules = [], [], []
        def flush():
            if current_agents:
                groups.append((tuple(current_agents), tuple(current_rules)))
                current_agents.clear()
                current_rules.clear()
        for line in lines + [""]:
            if not line:
                flush()
                continue
            key, separator, value = line.partition(":")
            if not separator:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if current_rules:
                    flush()
                current_agents.append(value.lower())
            elif key in ("allow", "disallow") and current_agents:
                current_rules.append((key, value))
        for agents, rules in groups:
            if "*" not in agents and "googlebot" not in agents:
                continue
            for path in ("/", "/directory"):
                # Conservative check: a root-wide Disallow without an equally
                # broad Allow should be reviewed; full robots matching remains
                # in the existing dedicated live crawl audit.
                if any(key == "disallow" and value == "/" for key, value in rules) and not any(
                    key == "allow" and value == "/" for key, value in rules
                ):
                    errors.append(f"/robots.txt: potential Googlebot block for {path}")
    except Exception as exc:
        errors.append(f"robots fetch/parse error ({type(exc).__name__}: {exc})")
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
    # Take a deterministic sample of crosslinked posts. The generated HTML is
    # the source of truth; no hand-written links or URL guesses are used.
    samples = {}
    for file in sorted(Path("dist/blog").glob("*/index.html"), reverse=True):
        html = file.read_text(encoding="utf-8")
        if related_targets(html):
            samples["/blog/" + file.parent.name + "/"] = html
            if len(samples) == 3:
                break
    errors, observations = check(
        source, article_sources=samples,
        directory_source=Path("dist/directory.html").read_text(encoding="utf-8"),
        script_source=Path("dist/assets/directory.js").read_text(encoding="utf-8"),
        category_sources={
            "/categories/education": Path("dist/categories/education.html").read_text(encoding="utf-8"),
        },
        maintenance_source=Path("dist/guides/directory-maintenance.html").read_text(encoding="utf-8"),
        category_hub_source=Path("dist/categories/index.html").read_text(encoding="utf-8"),
    )
    print("# Public release consistency (NOT Google indexing or search rankings)")
    for line in observations: print("- " + line)
    print(f"Result: {'FAIL' if errors else 'PASS'} ({len(errors)} issues)")
    for line in errors: print("- " + line)
    return int(bool(errors))

if __name__ == "__main__":
    sys.exit(main())
