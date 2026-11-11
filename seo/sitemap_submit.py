#!/usr/bin/env python3
"""Verify the public LinkWiki sitemap before a bounded GSC resubmission.

This uses Google's official Sitemaps API (not the unsupported general-purpose
Indexing API). It never claims submission equals downloading or indexing.
No URL Inspection or crawl automation is performed.
"""
import json
import os
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SITE = "https://linkwiki.info"
PROPERTY = "sc-domain:linkwiki.info"
SITEMAP = SITE + "/sitemap.xml"
API = "https://www.googleapis.com/webmasters/v3/sites/"
SCOPES = ["https://www.googleapis.com/auth/webmasters"]


def validate_public_sitemap(xml_bytes):
    """Return valid canonical URLs; reject unexpected hosts, duplicates and bad XML."""
    if len(xml_bytes) > 4_000_000:
        raise ValueError("sitemap exceeds expected byte limit")
    root = ET.fromstring(xml_bytes)
    if root.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
        raise ValueError("not a standard urlset")
    locations = [node.text or "" for node in root.findall(
        "{http://www.sitemaps.org/schemas/sitemap/0.9}url/"
        "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
    )]
    if len(locations) < 15 or len(locations) != len(set(locations)):
        raise ValueError("missing or duplicate canonical entries")
    for item in locations:
        parsed = urlsplit(item)
        if (parsed.scheme != "https" or parsed.netloc != "linkwiki.info"
                or parsed.query or parsed.fragment
                or parsed.path.endswith(".html")
                or "//" in parsed.path):
            raise ValueError("noncanonical or external sitemap URL")
    for required in (SITE + "/", SITE + "/directory", SITE + "/categories/"):
        if required not in locations:
            raise ValueError("required SEO landing page missing: " + required)
    return locations


def fetch_xml(fetch=urlopen):
    request = Request(SITEMAP, headers={
        "User-Agent": "LinkWiki-GSC-Sitemap-Verification/1.0",
        "Accept": "application/xml, text/xml"
    })
    with fetch(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError("public sitemap returned non-200")
        if urlsplit(response.geturl()).geturl() != SITEMAP:
            raise RuntimeError("public sitemap redirects away from canonical URL")
        return response.read(4_000_001)


def authorization_token():
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as AuthRequest
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON secret missing")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=SCOPES)
    credentials.refresh(AuthRequest())
    return credentials.token


def list_registered(token, fetch=urlopen):
    endpoint = API + quote(PROPERTY, safe="") + "/sitemaps"
    req = Request(endpoint, headers={"Authorization": "Bearer " + token})
    with fetch(req, timeout=30) as response:
        result = json.load(response)
    return result.get("sitemap", [])


def should_submit(items):
    """Only resubmit if no successful fetch exists for the canonical sitemap."""
    current = next((row for row in items if row.get("path") == SITEMAP), None)
    if current is None:
        return True, "canonical sitemap not registered"
    if current.get("lastDownloaded"):
        return False, "canonical sitemap already downloaded by Google"
    if int(current.get("errors") or 0) > 0:
        return True, "Google reported sitemap processing errors"
    return True, "canonical sitemap has no recorded download"


def submit_sitemap(token, fetch=urlopen):
    endpoint = API + quote(PROPERTY, safe="") + "/sitemaps/" + quote(SITEMAP, safe="")
    req = Request(endpoint, data=b"", method="PUT",
                  headers={"Authorization": "Bearer " + token,
                           "Content-Length": "0"})
    with fetch(req, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError("GSC sitemap submission did not return success")
    return True


def main():
    # No Google API mutation before exact public URL and sitemap contents pass.
    urls = validate_public_sitemap(fetch_xml())
    print(f"PUBLIC_SITEMAP_VALID: {len(urls)} canonical URLs")
    token = authorization_token()
    registered = list_registered(token)
    needed, reason = should_submit(registered)
    print("GSC_DECISION:", reason)
    if not needed:
        print("GSC_SITEMAP_ACTION: skipped_already_downloaded")
        return
    submit_sitemap(token)
    # A successful PUT only means request accepted, not Google processed or indexed.
    print("GSC_SITEMAP_ACTION: submitted_to_google_pending_processing")


if __name__ == "__main__":
    main()
