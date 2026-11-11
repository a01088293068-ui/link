#!/usr/bin/env python3
"""Read-only, bounded health observations for published LinkWiki destinations.

HEAD observations are not proof that a service is safe or owned by its claimed
operator. They must not silently rewrite the public catalog or annotate cards
as independently verified. Redirects, 403, bot protection and timeouts are
review signals, never grounds for automatic deletion.
"""
import argparse
from datetime import datetime, date, timezone
import ipaddress
import json
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "verified-directory.json"
OUTPUT = ROOT / "seo" / "external-link-observations.json"
DEFAULT_BATCH = 24
MAX_BATCH = 30


def safe_target(url):
    """Allow public-appearing HTTPS hostnames only; no IP or private aliases."""
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise ValueError("unacceptable URL")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or
            parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.fragment):
        raise ValueError("catalog URL must be an HTTPS public hostname")
    host = parsed.hostname.strip(".").lower()
    if (host in {"localhost", "local", "metadata.google.internal"}
            or host.endswith((".localhost", ".local", ".internal"))
            or host.count(".") < 1):
        raise ValueError("local/host-only URL prohibited")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP addresses prohibited")
    if any(not part or part.startswith("-") or part.endswith("-") for part in host.split(".")):
        raise ValueError("invalid hostname")
    return url


def catalog_entries(source=DATA):
    items = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(items, list) or len(items) < 1:
        raise ValueError("empty catalog")
    known = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("invalid catalog entry")
        url = safe_target(item.get("url"))
        if url in known:
            raise ValueError("duplicate catalog link")
        known.add(url)
    return items


def select_batch(entries, day, batch_size=DEFAULT_BATCH):
    if not 1 <= batch_size <= MAX_BATCH:
        raise ValueError("invalid batch size")
    if not entries:
        return []
    # Fixed launch anchor yields stable consecutive-day round robin.
    number = (day - date(2026, 11, 11)).days
    first = (number * batch_size) % len(entries)
    return [entries[(first + i) % len(entries)]
            for i in range(min(batch_size, len(entries)))]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def classify_status(code):
    if 200 <= code < 300:
        return "http_responded"
    if 300 <= code < 400:
        return "redirect_review"
    if code in (401, 403, 405, 429, 451):
        return "access_limited"
    if 400 <= code < 600:
        return "http_error_review"
    return "unexpected_response"


def check_url(url, opener=None, timeout=8):
    safe_target(url)
    if opener is None:
        opener = build_opener(HTTPSHandler(), NoRedirect())
    request = Request(url, method="HEAD", headers={
        "User-Agent": "LinkWiki-Directory-Maintenance/1.0",
        "Accept": "*/*",
    })
    try:
        with opener.open(request, timeout=timeout) as resp:
            return {"status": classify_status(resp.status), "http_code": resp.status}
    except HTTPError as exc:
        return {"status": classify_status(exc.code), "http_code": exc.code}
    except (URLError, TimeoutError, ConnectionError, socket.timeout, OSError) as exc:
        # Never reveal detailed external HTML, credentials or network internals.
        return {"status": "network_uncertain", "error_type": type(exc).__name__}


def run(day, entries, batch_size=DEFAULT_BATCH, observer=check_url):
    batch = select_batch(entries, day, batch_size=batch_size)
    findings = []
    for entry in batch:
        observed = observer(entry["url"])
        findings.append({
            "name": entry["name"], "url": entry["url"],
            "category": entry["category"], "observation": observed,
        })
    return {
        "date_utc": day.isoformat(),
        "checked_count": len(findings),
        "catalog_count": len(entries),
        "method": "HEAD without following redirects",
        "disclaimer": (
            "HTTP response observations only. Does not verify official ownership, "
            "safety, active user flows, or full site functionality. Never automatically "
            "delete records from inconclusive or failed HTTP observations."
        ),
        "results": findings,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--date", default=None)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    args = parser.parse_args()
    today = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    result = run(today, catalog_entries(args.catalog), batch_size=args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for row in result["results"]:
        kind = row["observation"]["status"]
        counts[kind] = counts.get(kind, 0) + 1
    print("CATALOG_COUNT:", result["catalog_count"])
    print("LINKS_OBSERVED:", result["checked_count"])
    print("OBSERVATION_COUNTS:", json.dumps(counts, ensure_ascii=False, sort_keys=True))
    print("NOTE: Observations are not third-party verification or automatic removal instructions.")


if __name__ == "__main__":
    main()
