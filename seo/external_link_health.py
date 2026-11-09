#!/usr/bin/env python3
"""Bounded read-only verification of real external listings for site upkeep.

No content extraction, crawling, auth, forms, submissions or automatic deletion.
403/429/network errors are NOT described as dead external websites.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from urllib.request import build_opener, HTTPRedirectHandler, Request
from urllib.error import HTTPError, URLError
from ipaddress import ip_address
import argparse
import json
import socket

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "verified-directory.json"
REPORT = ROOT / "seo" / "external-link-health-report.md"
TIMEOUT = 7
MAX_WORKERS = 8

class NoFollowRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None

OPENER = build_opener(NoFollowRedirects)

def safe_url(value):
    """Reject credentials, non-public IP literals, query-less fake hosts."""
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or
                parsed.username or parsed.password or parsed.port not in (None, 443)):
            return False
        host = parsed.hostname
        if host in ("localhost",) or host.endswith((".local", ".internal", ".localhost")):
            return False
        try:
            return ip_address(host).is_global
        except ValueError:
            return "." in host
    except (ValueError, TypeError):
        return False

def classify(code):
    if code in (200, 204, 206):
        return "reachable"
    if 300 <= code < 400:
        return "redirect_review"
    if code in (404, 410):
        return "broken_candidate"
    if code in (401, 403, 405, 429, 451):
        return "restricted_or_unknown"
    if code >= 500:
        return "server_error_unconfirmed"
    return "unknown"

def check_entry(entry, opener=OPENER):
    name = str(entry.get("name") or "").strip()
    category = str(entry.get("category") or "").strip()
    url = str(entry.get("url") or "").strip()
    if not safe_url(url):
        return {"name": name, "category": category, "url": url,
                "http": "-", "status": "invalid_url", "redirect": "-"}
    request = Request(url, headers={"User-Agent": "LinkWiki-Listing-Health/1.0",
                                    "Accept": "text/html,*/*;q=0.1"}, method="HEAD")
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            code = response.status
            location = response.headers.get("Location", "")
    except HTTPError as e:
        code = e.code
        location = e.headers.get("Location", "") if e.headers else ""
        e.close()
    except (URLError, TimeoutError, ConnectionError, OSError, socket.timeout):
        return {"name": name, "category": category, "url": url,
                "http": "-", "status": "network_unconfirmed", "redirect": "-"}
    redirect = "-"
    if 300 <= code < 400 and location:
        redirect_url = urljoin(url, location)
        redirect = redirect_url if safe_url(redirect_url) else "unsafe_or_non_https_target"
    return {"name": name, "category": category, "url": url,
            "http": str(code), "status": classify(code), "redirect": redirect}

def markdown_report(rows, checked_at):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    out = [
        "# LinkWiki external listing health — read-only HEAD audit", "",
        "Checked: " + checked_at, "",
        "This is a one-request-per-listing HEAD snapshot; many working websites "
        "block bots or HEAD requests. Neither a 403 nor a timeout proves a link "
        "is broken. **No entries are automatically modified or deleted.**",
        "",
        "## Counts", "",
        "| Outcome | Listings |", "|---|---:|",
    ]
    for state in sorted(counts):
        out.append("| " + state + " | " + str(counts[state]) + " |")
    out += ["", "## Items needing manual verification", "",
            "| Registered name | Category | URL | HTTP | Observation |",
            "|---|---|---|---:|---|"]
    flagged = [row for row in rows if row["status"] != "reachable"]
    if not flagged:
        out.append("| None | - | - | - | - |")
    for row in flagged:
        clean = lambda text: str(text).replace("|", "%7C").replace("\n", " ")
        out.append("| " + " | ".join(clean(row[key]) for key in
                   ("name", "category", "url", "http", "status")) + " |")
    out += ["", "## Limitations", "",
            "- 404/410 is a **candidate** for review, not immediate deletion: HEAD "
            "can differ from a real browser GET.",
            "- 3xx is recorded without following the redirect to avoid visiting "
            "unreviewed destinations.",
            "- 403, 405, 429, 451 and network problems require a manual browser "
            "check before concluding a site is unavailable.",
            "- No Google rankings, Googlebot accessibility, link safety, uptime "
            "guarantees, or latest-checked badges are inferred.", ""]
    return "\n".join(out)

def run(source=SOURCE, report=REPORT, workers=MAX_WORKERS, checker=check_entry):
    records = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("Expected nonempty list of verified directory source records")
    with ThreadPoolExecutor(max_workers=min(max(1, workers), 8)) as executor:
        rows = list(executor.map(checker, records))
    report = Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(markdown_report(rows, datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC")), encoding="utf-8")
    print("Checked", len(rows), "external listings; report:", report)
    print("Flagged for review:", sum(row["status"] != "reachable" for row in rows))
    return rows

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    args = parser.parse_args()
    run(source=args.source, report=args.report, workers=args.workers)
