#!/usr/bin/env python3
"""Verify the public LinkWiki sitemap before a bounded GSC resubmission.

This uses Google's official Sitemaps API (not the unsupported general-purpose
Indexing API). It never claims submission equals downloading or indexing.
No URL Inspection or crawl automation is performed.
"""
import json
import os
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SITE = "https://linkwiki.info"
PROPERTY = "sc-domain:linkwiki.info"
SITEMAP = SITE + "/sitemap.xml"
API = "https://www.googleapis.com/webmasters/v3/sites/"
SCOPES = ["https://www.googleapis.com/auth/webmasters"]


def validate_public_sitemap(xml_bytes, required_urls=()):
    """Return canonical URLs; reject bad XML and pages missing from the live deploy."""
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
    required = (SITE + "/", SITE + "/directory", SITE + "/categories/")
    for item in tuple(required) + tuple(required_urls):
        if item not in locations:
            raise ValueError("required deployed SEO URL missing: " + item)
    return locations


def expected_public_urls(root=None):
    """List source-backed pages the current deployment must expose before submission."""
    source = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    expected = []
    for directory, prefix in (("categories", "/categories/"), ("guides", "/guides/")):
        folder = source / directory
        if folder.is_dir():
            for page in sorted(folder.glob("*.html")):
                if page.stem != "index":
                    expected.append(SITE + prefix + page.stem)
    content = source / "content"
    if content.is_dir():
        for article in sorted(content.glob("*.md")):
            if article.is_file() and article.read_text(encoding="utf-8-sig").lstrip().startswith("# "):
                expected.append(SITE + "/blog/" + article.stem + "/")
    return tuple(expected)


def latest_sitemap_lastmod(xml_bytes):
    """Return the newest explicit sitemap lastmod date, without inventing dates."""
    root = ET.fromstring(xml_bytes)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    values = []
    for node in root.findall(f"{ns}url/{ns}lastmod"):
        if node.text:
            value = node.text.strip()[:10]
            try:
                values.append(date.fromisoformat(value))
            except ValueError as error:
                raise ValueError("invalid sitemap lastmod date") from error
    return max(values).isoformat() if values else None


def fetch_deployed_sitemap(expected_urls=(), fetch=urlopen, attempts=10,
                           delay_seconds=12, sleep=None):
    """Wait for Pages deployment to publish all source-backed URLs before GSC actions."""
    if attempts < 1 or delay_seconds < 0:
        raise ValueError("invalid sitemap deployment wait configuration")
    sleep = sleep or time.sleep
    last_error = None
    for attempt in range(attempts):
        xml_bytes = fetch_xml(fetch)
        try:
            urls = validate_public_sitemap(xml_bytes, required_urls=expected_urls)
            return xml_bytes, urls
        except ValueError as error:
            last_error = error
            if attempt + 1 < attempts:
                sleep(delay_seconds)
    raise RuntimeError(
        "public sitemap did not catch up with the current deployment: " + str(last_error)
    )


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


def should_submit(items, newest_lastmod=None):
    """Submit when Google has not downloaded the sitemap or the published XML changed later."""
    current = next((row for row in items if row.get("path") == SITEMAP), None)
    if current is None:
        return True, "canonical sitemap not registered"
    if int(current.get("errors") or 0) > 0:
        return True, "Google reported sitemap processing errors"
    if current.get("isPending") is True:
        return False, "canonical sitemap is already pending Google processing"
    downloaded = current.get("lastDownloaded")
    if downloaded:
        downloaded_day = str(downloaded)[:10]
        if newest_lastmod and newest_lastmod > downloaded_day:
            return True, "published sitemap lastmod is newer than Google's last download"
        return False, "canonical sitemap already downloaded after its latest published update"
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
    # Wait for Pages to finish deploying this commit. A pre-deploy sitemap can
    # be valid XML yet omit the new article/category URLs and must never be
    # treated as the current release.
    expected = expected_public_urls()
    xml_bytes, urls = fetch_deployed_sitemap(expected)
    newest_lastmod = latest_sitemap_lastmod(xml_bytes)
    print(f"PUBLIC_SITEMAP_VALID: {len(urls)} canonical URLs")
    print("PUBLIC_SITEMAP_NEWEST_LASTMOD:", newest_lastmod or "not provided")
    token = authorization_token()
    registered = list_registered(token)
    needed, reason = should_submit(registered, newest_lastmod=newest_lastmod)
    print("GSC_DECISION:", reason)
    if not needed:
        print("GSC_SITEMAP_ACTION: skipped_already_downloaded")
        return
    submit_sitemap(token)
    # A successful PUT only means request accepted, not Google processed or indexed.
    print("GSC_SITEMAP_ACTION: submitted_to_google_pending_processing")


if __name__ == "__main__":
    main()
