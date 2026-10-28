#!/usr/bin/env python3
"""Official Viesearch submission API adapter, with dry-run and deduplication.

Viesearch API docs: https://viesearch.com/api/post-submit
An API response means submitted for manual review, not a live backlink.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

try:
    from seo import backlink_manager as ledger
except ModuleNotFoundError:
    import backlink_manager as ledger

API = "https://viesearch.com/api/submit"
SUBMIT_PAGE = "https://viesearch.com/submit"


def existing_viesearch_entry(registry):
    for entry in registry["entries"]:
        if entry["platform"].strip().lower() == "viesearch":
            return entry
    return None


def submit(api_key, payload):
    request = urllib.request.Request(API, method="POST",
        headers={"x-api-key": api_key, "Content-Type": "application/json", "Accept": "application/json"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    with urllib.request.urlopen(request, timeout=25) as response:
        body = json.load(response)
    if body.get("success") is not True:
        raise RuntimeError("Viesearch rejected submission: " + str(body.get("message", "unknown error")))
    return body


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="https://linkwiki.info/")
    p.add_argument("--title", default="LinkWiki")
    p.add_argument("--description", default="Korean-language website directory with organized links and browsing guides.")
    p.add_argument("--category", default="computers_and_technology")
    p.add_argument("--registry", type=Path, default=ledger.REGISTRY)
    p.add_argument("--execute", action="store_true", help="Send one real API submission (dry-run by default)")
    args = p.parse_args()
    target = ledger.validate_url(args.url)
    registry = ledger.load_registry(args.registry)
    previous = existing_viesearch_entry(registry)
    if previous and previous["submission_status"] in {"submitted", "pending_review", "approved"}:
        print("SKIP: Viesearch already submitted/approved; do not send duplicate request")
        return
    payload = {"url": target, "title": args.title, "description": args.description,
               "category_slug": args.category}
    if not args.execute:
        print(json.dumps({"dry_run": True, "endpoint": API, "payload": payload}, ensure_ascii=False, indent=2))
        return
    key = os.getenv("VIESEARCH_API_KEY", "").strip()
    if not key:
        p.error("Set VIESEARCH_API_KEY from your Viesearch account settings")
    try:
        response = submit(key, payload)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Viesearch returned HTTP {exc.code}; no success recorded") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(f"Viesearch network failure; check their dashboard before retrying: {exc}") from exc
    # The official API returns a review token, but not a published link.
    token = response.get("token", "")
    if previous:
        entry = previous
    else:
        entry = {"id": ledger.key_for("Viesearch", SUBMIT_PAGE), "platform": "Viesearch",
                 "submission_url": SUBMIT_PAGE, "public_url": "", "audit_status": "unverified",
                 "last_checked": "", "http_status": None, "link_found": False,
                 "rel": [], "noindex": None, "notes": ""}
        registry["entries"].append(entry)
    entry["submission_status"] = "pending_review"
    entry["notes"] = ("Official API accepted for review; token " + str(token)[:60]) if token else "Official API accepted for review"
    ledger.save_registry(args.registry, registry)
    print("SUBMITTED FOR REVIEW, NOT YET A VERIFIED BACKLINK")


if __name__ == "__main__":
    main()
