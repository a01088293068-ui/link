#!/usr/bin/env python3
"""Read-only publication discovery for previously submitted, still-pending sites.

Search results alone are never verified backlinks. The final report counts only
direct HTML hyperlinks found on the actual public source page. This script
never creates accounts, follows submission forms, or sends registration data.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from seo import backlink_manager

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "seo/backlink-registry.json"
JSON_REPORT = ROOT / "seo/backlink-pending-watch.json"
MD_REPORT = ROOT / "seo/backlink-pending-watch.md"
SERPER_URL = "https://google.serper.dev/search"
EXCLUDE_PATH_WORDS = (
    "/submit", "/sign-in", "/signin", "/login", "/register",
    "/terms", "/privacy", "/search", "/contact", "/about",
    "/cgi-bin/", "/portal/", "/add-url", "/get-featured",
)
PENDING = "pending_review"


def host(url):
    parsed = urlsplit(str(url))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return parsed.hostname.lower().removeprefix("www.")


def pending_hosts(registry):
    """Do not re-submit; watch at most one record per submitting domain."""
    known = {}
    for entry in registry["entries"]:
        if entry.get("submission_status") != PENDING or entry.get("public_url"):
            continue
        source_host = host(entry.get("submission_url"))
        if not source_host or source_host in known:
            continue
        # FreeWebSubmission is a bulk submission intermediary, not a
        # publication host; an accepted handoff is not a direct backlink.
        if source_host in {"freewebsubmission.com"}:
            continue
        known[source_host] = entry["platform"]
    return known


def query_serper(website, api_key):
    query = f'site:{website} "linkwiki.info"'
    payload = json.dumps({"q": query, "num": 10, "gl": "kr", "hl": "ko"}).encode()
    request = Request(SERPER_URL, data=payload, headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "X-API-KEY": api_key, "User-Agent": "LinkWiki-PublicationWatch/1.0",
    }, method="POST")
    with urlopen(request, timeout=20) as response:
        return json.load(response).get("organic", [])


def candidate_url(result, expected_host):
    url = str(result.get("link") or "")
    if host(url) != expected_host:
        return ""
    parsed = urlsplit(url)
    if parsed.query or parsed.fragment:
        # Avoid listing-site search URLs and tracker redirects.
        return ""
    path = parsed.path.lower()
    if not path or path == "/" or any(value in path for value in EXCLUDE_PATH_WORDS):
        return ""
    return url


def inspect(registry, search, fetch=backlink_manager.fetch_public):
    checked, errors, confirmed = [], [], set()
    hosts = pending_hosts(registry)
    for source_host, platform in sorted(hosts.items()):
        try:
            results = search(source_host)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append({"platform": platform, "error": type(exc).__name__})
            continue
        seen = set()
        for result in results:
            url = candidate_url(result, source_host)
            if not url or url in seen:
                continue
            seen.add(url)
            row = {"platform": platform, "source_host": source_host, "url": url,
                   "result": "unverified", "direct_link": False,
                   "noindex": None, "rel": []}
            try:
                status, html, xrobots, content_type = fetch(url)
                row["http_status"] = status
                if status == 200 and html and "html" in content_type.lower():
                    verdict, found, rels, noindex = backlink_manager.evaluate_html(
                        html, registry["target_domain"], xrobots)
                    row.update(result=verdict, direct_link=found,
                               noindex=noindex, rel=rels)
                    if verdict in {"verified_link", "link_with_rel"}:
                        confirmed.add(source_host)
                else:
                    row["result"] = "inconclusive_http_or_nonhtml"
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                row["result"] = "fetch_error"
                row["error"] = type(exc).__name__
            checked.append(row)
            if len(seen) >= 3:  # no more than 3 pages per source
                break
    return {
        "schema": 1, "target": "https://linkwiki.info/",
        "pending_hosts_considered": len(hosts),
        "checked_pages": checked, "errors": errors,
        "confirmed_domains": sorted(confirmed),
        "submitted_new": 0,
    }


def report(data):
    lines = [
        "# Pending backlink publication watcher", "",
        "Read-only check of *previously submitted* backlink providers. No new registrations.",
        "Search discovery is incomplete: absence of a search result is NOT proof of rejection.",
        "A direct live HTML link is different from Google recognizing or ranking it.", "",
        f'- Pending provider domains checked: {data["pending_hosts_considered"]}',
        f'- Public candidate pages inspected: {len(data["checked_pages"])}',
        f'- New direct-link domains reverified: {len(data["confirmed_domains"])}', "",
        "| Provider | Candidate page | Direct hyperlink state | Note |",
        "|---|---|---|---|",
    ]
    for row in data["checked_pages"]:
        title = row["platform"].replace("|", "/")
        url = row["url"].replace("|", "%7C")
        note = "rel=" + ",".join(row["rel"]) + "; noindex=" + str(row["noindex"])
        lines.append(f'| {title} | {url} | {row["result"]} | {note} |')
    if not data["checked_pages"]:
        lines.append("| No candidate found | - | unknown, not rejected | - |")
    if data["errors"]:
        lines.extend(["", "## Search errors", ""])
        lines.extend("- " + item["platform"] + ": " + item["error"]
                     for item in data["errors"])
    lines.extend(["", "No new form submissions; no registry auto-approval.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--json", type=Path, default=JSON_REPORT)
    parser.add_argument("--report", type=Path, default=MD_REPORT)
    args = parser.parse_args()
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        parser.error("SERPER_API_KEY required for submitted-domain discovery")
    registry = backlink_manager.load_registry(args.registry)
    data = inspect(registry, lambda source: query_serper(source, key))
    data["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    args.report.write_text(report(data), encoding="utf-8")
    print("Pending hosts", data["pending_hosts_considered"],
          "checked pages", len(data["checked_pages"]),
          "verified live domains", len(data["confirmed_domains"]),
          "search errors", len(data["errors"]))
    for row in data["checked_pages"]:
        print(row["platform"], row["result"], row["url"])


if __name__ == "__main__":
    main()
