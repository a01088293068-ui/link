#!/usr/bin/env python3
"""Read-only HTTP delivery checks for two public LinkWiki XML sitemaps.

This measures what an ordinary client receives, not what Googlebot received.
Never requests indexing or submits a sitemap. Runs on GitHub CI.
"""
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
import argparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://linkwiki.info"
SITEMAPS = (BASE + "/sitemap.xml", BASE + "/sitemap-v2.xml")
ROBOTS = BASE + "/robots.txt"
REPORT = ROOT / "seo/sitemap-http-report.md"


def fetch(url, opener=urlopen):
    request = Request(url, headers={
        "User-Agent": "LinkWiki-PublicSitemapAudit/1.0 (+read-only)",
        "Accept": "application/xml,text/xml,*/*;q=0.8",
        "Cache-Control": "no-cache",
    })
    with opener(request, timeout=20) as response:
        body = response.read(2_000_001)
        headers = response.headers
        return {
            "status": response.status,
            "url": response.geturl(),
            "content_type": headers.get("Content-Type", ""),
            "cache_control": headers.get("Cache-Control", ""),
            "etag": headers.get("ETag", ""),
            "body": body,
        }


def parse_sitemap(result):
    """No claim of live Google accessibility; validate XML and canonical URLs."""
    if result["status"] != 200:
        raise ValueError("HTTP status " + str(result["status"]))
    if len(result["body"]) > 2_000_000:
        raise ValueError("Response exceeded 2 MB diagnostic limit")
    if urlsplit(result["url"]).netloc != "linkwiki.info":
        raise ValueError("Sitemap redirected to an unexpected host")
    try:
        root = ET.fromstring(result["body"])
    except ET.ParseError as error:
        raise ValueError("XML parse error: " + str(error)) from error
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag != namespace + "urlset":
        raise ValueError("Unexpected XML root element")
    entries = []
    for url in root.findall(namespace + "url"):
        loc = url.findtext(namespace + "loc", default="").strip()
        parsed = urlsplit(loc)
        if parsed.scheme != "https" or parsed.netloc != "linkwiki.info":
            raise ValueError("Noncanonical sitemap URL")
        if parsed.query or parsed.fragment or parsed.path.endswith(".html"):
            raise ValueError("Sitemap contains a query, fragment or .html redirect URL")
        entries.append(loc)
    if not entries or len(entries) != len(set(entries)):
        raise ValueError("Empty or duplicate sitemap URL set")
    if BASE + "/" not in entries or BASE + "/directory" not in entries:
        raise ValueError("Homepage or full directory missing from sitemap")
    return entries


def check(fetcher=fetch):
    lines = [
        "# LinkWiki public sitemap HTTP diagnostics",
        "",
        "Checked UTC: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "",
        "Ordinary HTTP client responses only. This does NOT validate Google's fetch",
        "result or prove sitemap indexing, because Google's network and caches differ.",
        "",
        "| Sitemap | HTTP | Final URL | Content-Type | URL count | Check |",
        "|---|---:|---|---|---:|---|",
    ]
    errors = []
    groups = {}
    for url in SITEMAPS:
        try:
            result = fetcher(url)
            entries = parse_sitemap(result)
            groups[url] = set(entries)
            lines.append("| " + url + " | " + str(result["status"]) + " | " +
                         result["url"] + " | " + result["content_type"].replace("|", "/") +
                         " | " + str(len(entries)) + " | XML and URLs valid |")
            if "xml" not in result["content_type"].lower():
                errors.append(url + ": unexpected Content-Type " + result["content_type"])
        except (HTTPError, URLError, ValueError, TimeoutError, OSError, KeyError) as error:
            errors.append(url + ": " + type(error).__name__ + " " + str(error)[:200])
            lines.append("| " + url + " | - | - | - | - | unavailable/invalid |")
    if len(groups) == 2 and groups[SITEMAPS[0]] != groups[SITEMAPS[1]]:
        errors.append("sitemap.xml and sitemap-v2.xml URL sets differ")
    lines += ["", "## robots.txt", ""]
    try:
        result = fetcher(ROBOTS)
        if result["status"] != 200 or urlsplit(result["url"]).netloc != "linkwiki.info":
            raise ValueError("robots HTTP status or host invalid")
        data = result["body"].decode("utf-8-sig")
        directives = [line.strip() for line in data.splitlines()
                      if line.strip().lower().startswith("sitemap:")]
        for url in SITEMAPS:
            if not any(item.split(":", 1)[1].strip() == url for item in directives):
                errors.append("robots.txt missing directive for " + url)
        lines.append("Published Sitemap directives: " +
                     ", ".join(item.split(":", 1)[1].strip() for item in directives))
    except (HTTPError, URLError, ValueError, TimeoutError, OSError, KeyError) as error:
        errors.append("robots.txt: " + type(error).__name__ + " " + str(error)[:200])
        lines.append("Could not verify robots.txt")
    lines += ["", "## Verdict", ""]
    if errors:
        lines += ["HTTP or XML delivery problems detected:", ""]
        lines += ["- " + error for error in errors]
    else:
        lines.append("Both sitemaps and robots.txt were accessible and internally consistent to this client.")
    lines += ["", "If Google Search Console still reports 'Couldn't fetch' while this check passes,",
              "investigate Google-specific access, transient edge failures and GSC processing delays;",
              "do not assume the issue has been fixed or resubmit unchanged sitemaps repeatedly.", ""]
    return "\n".join(lines), errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    report, errors = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
