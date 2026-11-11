#!/usr/bin/env python3
"""Validate explicit Pages target before uploading any LinkWiki files.

No credentials are written to disk or printed.
"""
import json
import os
import re
import sys
from urllib.request import Request, urlopen

EXPECTED_DOMAIN = "linkwiki.info"
EXPECTED_BRANCH = "main"


def verify_project(response, project_name):
    if not isinstance(response, dict) or not response.get("success"):
        raise ValueError("Cloudflare project lookup failed")
    project = response.get("result") or {}
    if project.get("name") != project_name:
        raise ValueError("Cloudflare project name differs from configured target")
    if project.get("production_branch") != EXPECTED_BRANCH:
        raise ValueError("Cloudflare Pages production branch is not main")
    domains = project.get("domains") or []
    normalized = {str(x).lower().rstrip(".") for x in domains}
    if EXPECTED_DOMAIN not in normalized:
        raise ValueError("Selected Pages project does not serve linkwiki.info")
    return True


def main():
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    project = os.environ.get("CLOUDFLARE_PAGES_PROJECT", "").strip()
    if not token or not re.fullmatch(r"[a-fA-F0-9]{32}", account):
        raise ValueError("Cloudflare secret configuration missing or invalid")
    if not re.fullmatch(r"[a-z0-9-]+", project):
        raise ValueError("Cloudflare Pages project name invalid")
    url = (f"https://api.cloudflare.com/client/v4/accounts/{account}"
           f"/pages/projects/{project}")
    request = Request(url, headers={"Authorization": "Bearer " + token,
                                    "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    verify_project(payload, project)
    print("PASS: configured Pages project serves linkwiki.info from main")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FAIL: Pages target verification: " + type(error).__name__ +
              ": " + str(error).replace(os.environ.get("CLOUDFLARE_API_TOKEN", "") or "-----", "[secret]"),
              file=sys.stderr)
        sys.exit(1)
