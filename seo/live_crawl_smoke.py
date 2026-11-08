#!/usr/bin/env python3
"""Read-only deployed SEO smoke check. HTTP signals are not Google index status."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import json
import sys
import xml.etree.ElementTree as ET

ORIGIN = "https://linkwiki.info"
TARGETS = ("/", "/directory", "/categories/", "/robots.txt", "/sitemap.xml")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.links = []
        self.robots = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "meta" and attrs.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(attrs.get("content", "").lower())


def google_noindex(directives):
    """Detect Google-applicable noindex in mixed X-Robots-Tag directives.

    A header can mix unscoped directives and crawler-specific directives.
    Do not discard an earlier unscoped noindex because a later token has a
    bot prefix, or mistakenly attribute OtherBot rules to Googlebot.
    """
    for raw in directives:
        scope = None
        for token in str(raw).lower().split(","):
            directive = token.strip()
            if ":" in directive:
                agent, remaining = directive.split(":", 1)
                agent = agent.strip()
                if agent in ("googlebot", "googlebot-news", "*", "otherbot"):
                    scope = agent
                    directive = remaining.strip()
            if scope in (None, "googlebot", "*") and directive in ("noindex", "none"):
                return True
    return False


def fetch(path):
    req = Request(ORIGIN + path, headers={"User-Agent": "LinkWiki-SEO-Smoke/1.0"})
    with urlopen(req, timeout=15) as res:
        final_url = res.geturl()
        if urlsplit(final_url).hostname != "linkwiki.info":
            raise RuntimeError("unexpected redirect destination")
        return (res.status, final_url, res.read(1_000_000).decode("utf-8", "replace"),
                res.headers.get_all("X-Robots-Tag", []))


def inspect(fetcher=fetch):
    findings, records, bodies = [], [], {}
    response_headers = {}
    for path in TARGETS:
        try:
            response = fetcher(path)
            if len(response) == 3:
                status, final_url, body = response
                x_robots = []
            else:
                status, final_url, body, x_robots = response
            records.append((path, status, final_url))
            bodies[path] = body
            response_headers[path] = x_robots
            if status != 200:
                findings.append(f"{path}: HTTP {status}")
            if urlsplit(final_url).path != path:
                findings.append(f"{path}: redirects to {final_url}")
        except Exception as exc:
            records.append((path, "ERROR", type(exc).__name__))
            findings.append(f"{path}: {type(exc).__name__}: {str(exc)[:150]}")
    for path in ("/", "/directory", "/categories/"):
        if path not in bodies:
            continue
        parser = PageParser()
        parser.feed(bodies[path])
        expected = ORIGIN + path
        if parser.canonicals != [expected]:
            findings.append(f"{path}: canonical {parser.canonicals!r} != {expected}")
        if google_noindex(parser.robots):
            findings.append(f"{path}: HTML robots noindex directive found")
        if google_noindex(response_headers.get(path, [])):
            findings.append(f"{path}: X-Robots-Tag HTTP noindex directive found")
        if path == "/" and not any(link in ("/directory", "/directory.html", ORIGIN + "/directory") for link in parser.links):
            findings.append("/: no crawlable link to /directory")
    if "/robots.txt" in bodies:
        robots = bodies["/robots.txt"]
        declared_sitemaps = [
            line.split(":", 1)[1].strip()
            for raw in robots.splitlines()
            if (line := raw.partition("#")[0].strip())
            and line.lower().startswith("sitemap:")
        ]
        if ORIGIN + "/sitemap.xml" not in declared_sitemaps:
            findings.append("robots.txt: canonical sitemap not declared")
        rules = RobotFileParser()
        rules.parse(robots.splitlines())
        for path in ("/", "/directory", "/categories/"):
            if not rules.can_fetch("Googlebot", ORIGIN + path):
                findings.append(f"robots.txt: Googlebot disallowed {path}")
    if "/sitemap.xml" in bodies:
        try:
            root = ET.fromstring(bodies["/sitemap.xml"])
            urls = [e.text for e in root.iter() if e.tag.endswith("}loc")]
            if ORIGIN + "/directory" not in urls:
                findings.append("sitemap.xml: /directory missing")
            if ORIGIN + "/" not in urls:
                findings.append("sitemap.xml: homepage missing")
            # Detect redirecting or duplicate URLs before sending them to Google.
            if len(urls) != len(set(urls)):
                findings.append("sitemap.xml: duplicate URL entries")
            for url in urls:
                parts = urlsplit(url or "")
                if parts.scheme != "https" or parts.netloc != "linkwiki.info":
                    findings.append(f"sitemap.xml: off-origin or invalid URL {url!r}")
                elif parts.query or parts.fragment or parts.path.endswith(".html"):
                    findings.append(f"sitemap.xml: noncanonical URL {url!r}")
        except ET.ParseError:
            findings.append("sitemap.xml: invalid XML")
    return findings, records


def main():
    findings, records = inspect()
    lines = ["# LinkWiki deployment SEO smoke check", "",
             "Run: " + datetime.now(timezone.utc).isoformat(), "",
             "This tests live HTTP responses, not Google indexing or rankings.", "",
             "| URL | HTTP | final URL / error |", "|---|---|---|"]
    for path, status, destination in records:
        lines.append("| " + path + " | " + str(status) + " | " + destination.replace("|", "%7C") + " |")
    lines.extend(["", "## Findings", ""])
    lines.extend("- " + item for item in findings) if findings else lines.append("No live HTTP SEO blockers detected.")
    output = Path("seo/live-crawl-report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
