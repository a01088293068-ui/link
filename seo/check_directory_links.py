#!/usr/bin/env python3
"""Audit external link reachability without assuming blocked bots mean dead URLs.

The generated report is private to GitHub Actions. Never rewrites the live
directory or claims every link was manually verified.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "assets" / "verified-directory.json"
OUTPUT = ROOT / "seo" / "directory-reachability.json"


def check(record, timeout=8):
    url = record["url"]
    request = Request(url, headers={"User-Agent": "LinkWiki-LinkAudit/1.0 (+https://linkwiki.info/)"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            final_url = response.url
    except HTTPError as error:
        status = error.code
        final_url = error.url
    except (URLError, TimeoutError, OSError) as error:
        return {"name": record["name"], "url": url, "result": "unreachable",
                "detail": type(error).__name__}
    # HTTP 200 alone is not proof the submitted destination still resolves
    # to the same service. Flag cross-host redirects and HTTPS downgrades for
    # human review, but never silently delete the registered directory link.
    origin = urlsplit(url)
    landed = urlsplit(final_url)
    redirected_host = (landed.hostname or "").lower() != (origin.hostname or "").lower()
    downgraded = origin.scheme == "https" and landed.scheme != "https"
    # 401/403/429 often reflect access control or bot blocking, not dead links.
    category = ("access_restricted" if status in (401, 403, 405, 429) else
                "not_found" if status in (404, 410) else
                "needs_review" if redirected_host or downgraded else
                "ok" if 200 <= status < 400 else "needs_review")
    result = {"name": record["name"], "url": url, "result": category,
              "http_status": status, "final_url": final_url}
    if redirected_host:
        result["redirect_warning"] = "destination_hostname_changed"
    if downgraded:
        result["security_warning"] = "https_downgrade"
    return result


def run(records, workers=8, timeout=8):
    results = [None] * len(records)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check, record, timeout): idx
                   for idx, record in enumerate(records)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be in 1..16")
    records = json.loads(args.input.read_text(encoding="utf-8"))
    results = run(records, args.workers)
    payload = {"checked_at": datetime.now(timezone.utc).isoformat(),
               "total": len(results), "results": results,
               "note": "An HTTP check is not an endorsement or proof of current official ownership."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {name: sum(item["result"] == name for item in results)
              for name in ("ok", "access_restricted", "not_found", "needs_review", "unreachable")}
    print("Directory audit:", counts)


if __name__ == "__main__":
    main()
