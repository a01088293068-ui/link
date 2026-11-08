#!/usr/bin/env python3
"""One guarded official Google Search Console sitemap re-submission.

Run only after a successful verified public deployment. It does not request
indexing of individual pages or promise Google crawling, indexing or ranking.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

PROPERTY = 'sc-domain:linkwiki.info'
SITEMAP = 'https://linkwiki.info/sitemap.xml'
SCOPE = 'https://www.googleapis.com/auth/webmasters'
CORE_URLS = (SITEMAP.removesuffix('/sitemap.xml') + '/',
             'https://linkwiki.info/directory',
             'https://linkwiki.info/categories/') + tuple(
    'https://linkwiki.info/categories/' + slug for slug in
    ('community', 'korean', 'comics-directory', 'webtoon',
     'ai', 'search', 'sports', 'video'))


def access_token():
    from google.auth.transport.requests import Request as AuthRequest
    from google.oauth2 import service_account
    raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip()
    if not raw:
        return None
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=[SCOPE])
    credentials.refresh(AuthRequest())
    return credentials.token


def list_sitemaps(token, site=PROPERTY):
    endpoint = ('https://www.googleapis.com/webmasters/v3/sites/' +
                quote(site, safe='') + '/sitemaps')
    request = Request(endpoint, headers={'Authorization': 'Bearer ' + token},
                      method='GET')
    with urlopen(request, timeout=25) as response:
        return json.load(response).get('sitemap', [])


def submit_sitemap(token, site=PROPERTY):
    """Official Sitemaps: submit; submit exactly one fixed, public sitemap."""
    endpoint = ('https://www.googleapis.com/webmasters/v3/sites/' +
                quote(site, safe='') + '/sitemaps/' + quote(SITEMAP, safe=''))
    request = Request(endpoint, headers={'Authorization': 'Bearer ' + token},
                      method='PUT')
    with urlopen(request, timeout=25) as response:
        if response.status not in (200, 204):
            raise RuntimeError('Sitemap submit unexpected HTTP status ' + str(response.status))


def parse_submitted(timestamp):
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None
    try:
        value = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        return None
    return value.astimezone(timezone.utc) if value.tzinfo else None


def eligible(row, now=None):
    """Only long-stalled, never-downloaded, registered sitemap submissions."""
    if not row or row.get('path') != SITEMAP:
        return False, 'no exact submitted sitemap record'
    if row.get('isPending') is not True:
        return False, 'sitemap not pending'
    if row.get('lastDownloaded'):
        return False, 'Google already downloaded sitemap'
    try:
        errors = int(row.get('errors') or 0)
    except (ValueError, TypeError):
        return False, 'invalid Google error count'
    if errors > 0:
        return False, 'sitemap has Google parsing errors'
    submitted = parse_submitted(row.get('lastSubmitted'))
    if submitted is None:
        return False, 'submission time unknown'
    now = now or datetime.now(timezone.utc)
    if now - submitted < timedelta(days=7):
        return False, 'last submission less than seven days ago'
    return True, 'pending without download for at least seven days'


def sitemap_entries(xml_bytes):
    root = ET.fromstring(xml_bytes)
    result = {}
    for entry in root:
        loc = None
        lastmod = None
        for child in entry:
            if child.tag.rsplit('}', 1)[-1] == 'loc':
                loc = child.text
            elif child.tag.rsplit('}', 1)[-1] == 'lastmod':
                lastmod = child.text
        if loc:
            if loc in result:
                raise ValueError('duplicate sitemap URL ' + loc)
            result[loc] = lastmod
    return result


def public_release_is_verified(dist, fetch=None):
    """Revalidate live sitemap against generated URL list and core edit dates."""
    expected = sitemap_entries((dist / 'sitemap.xml').read_bytes())
    if not set(CORE_URLS).issubset(expected):
        raise RuntimeError('Expected release missing canonical core pages')
    if fetch is None:
        def fetch():
            request = Request(SITEMAP, headers={'User-Agent': 'LinkWiki-GSC-SitemapRecovery/1.0'})
            with urlopen(request, timeout=25) as response:
                if response.status != 200 or response.geturl() != SITEMAP:
                    raise RuntimeError('Public sitemap unexpected HTTP response/redirect')
                return response.read()
    actual = sitemap_entries(fetch())
    if actual != expected:
        raise RuntimeError('Public sitemap does not match verified generated release')
    return True


def recover(token, dist, now=None, list_fn=list_sitemaps, submit_fn=submit_sitemap,
            fetch=None):
    rows = list_fn(token)
    candidate = next((item for item in rows if item.get('path') == SITEMAP), None)
    allowed, reason = eligible(candidate, now)
    if not allowed:
        return 'SKIP: ' + reason
    public_release_is_verified(dist, fetch)
    submit_fn(token)
    return 'SUBMITTED: one official resubmission for a seven-day-stalled sitemap; Google processing pending'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dist', type=Path, required=True)
    args = parser.parse_args()
    if not args.dist.is_dir():
        parser.error('Verified build directory missing')
    if os.environ.get('GSC_PROPERTY', PROPERTY) not in ('', PROPERTY):
        raise SystemExit('GSC property differs from expected LinkWiki property; no submission')
    if not os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip():
        print('::warning::GSC credentials not configured; sitemap resubmission not attempted')
        return 0
    try:
        token = access_token()
        message = recover(token, args.dist)
        print(message)
        return 0
    except Exception as exc:
        # Never log the secret, token or raw API response body.
        status = getattr(exc, 'code', None)
        info = type(exc).__name__ + (f' HTTP {status}' if status else '')
        print('::warning::GSC sitemap recovery not confirmed: ' + info)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
