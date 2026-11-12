#!/usr/bin/env python3
"""Read-only Search Console performance snapshot for LinkWiki.

Requires GOOGLE_SERVICE_ACCOUNT_JSON (JSON string) or
GOOGLE_APPLICATION_CREDENTIALS (path); a service-account email must have
Search Console property access. Never commits credentials or raw tokens.
"""
import argparse
from datetime import date, timedelta
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / 'seo' / 'search-console-report.md'
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']


def access_token():
    try:
        from google.auth.transport.requests import Request as AuthRequest
        from google.oauth2 import service_account
    except ImportError as exc:
        raise RuntimeError('Install google-auth and requests (see setup guide)') from exc
    raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip()
    if raw:
        credentials = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        credentials = service_account.Credentials.from_service_account_file(
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'], scopes=SCOPES)
    else:
        raise RuntimeError('Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS')
    credentials.refresh(AuthRequest())
    return credentials.token


def query_performance(token, property_url, start_date, end_date, dimensions, limit=100,
                      filter_groups=None):
    endpoint = ('https://www.googleapis.com/webmasters/v3/sites/' +
                quote(property_url, safe='') + '/searchAnalytics/query')
    payload = {'startDate': start_date, 'endDate': end_date, 'dimensions': dimensions,
               'rowLimit': limit, 'type': 'web'}
    if filter_groups is not None:
        payload['dimensionFilterGroups'] = filter_groups
    request = Request(endpoint, json.dumps(payload).encode('utf-8'),
                      {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                      method='POST')
    # Read-only Search Analytics requests occasionally time out transiently.
    # Retrying only 429/5xx, socket timeout and transport errors avoids aborting
    # the entire daily snapshot; do not repeat credential or permission errors.
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response).get('rows', [])
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError('unreachable GSC retry state')


INSPECT_URLS = (
    'https://linkwiki.info/',
    'https://linkwiki.info/directory',
    'https://linkwiki.info/categories/',
    'https://linkwiki.info/categories/community',
    'https://linkwiki.info/categories/korean',
    'https://linkwiki.info/categories/comics-directory',
    'https://linkwiki.info/categories/webtoon',
    'https://linkwiki.info/categories/ai',
    'https://linkwiki.info/categories/search',
    'https://linkwiki.info/categories/sports',
    'https://linkwiki.info/categories/video',
    'https://linkwiki.info/guides/address-check',
    'https://linkwiki.info/guides/directory-comparison',
)



def recent_published_post_urls(limit=3):
    """Inspect recent generated articles even before they earn impressions."""
    posts = ROOT / "content"
    return [
        "https://linkwiki.info/blog/" + path.stem + "/"
        for path in sorted(posts.glob("seo-*.md"), reverse=True)[:limit]
    ]

# Recent task-specific articles linked directly from the canonical directory.
# These are checked only when the corresponding published Markdown exists;
# never send fabricated URLs to Google's URL Inspection API.
DIRECTORY_INTENT_ARTICLES = (
    "seo-20261111-address-directory-no-results",
    "seo-20261111-site-directory-selection-by-purpose",
    "seo-20261111-mobile-address-directory-check",
)


def directory_intent_inspection_urls():
    posts = ROOT / "content"
    return [
        "https://linkwiki.info/blog/" + slug + "/"
        for slug in DIRECTORY_INTENT_ARTICLES
        if (posts / (slug + ".md")).is_file()
    ]



def rotating_inspection_urls(as_of, limit=3, root=None):
    """Deterministically rotate actual published guide URLs across daily GSC runs.

    The mandatory homepage/category checks keep their existing priority. This
    optional rotation supplements them, so older guides with no impressions
    eventually receive an independent Google URL Inspection result.
    """
    if limit < 1:
        return []
    source = root if root is not None else ROOT
    posts = source / "content"
    urls = sorted({
        "https://linkwiki.info/blog/" + path.stem + "/"
        for path in posts.glob("*.md")
        if path.is_file() and len(path.read_text(encoding="utf-8-sig").strip()) >= 150
        and re.fullmatch(r"[A-Za-z0-9_-]+", path.stem)
    })
    if not urls:
        return []
    day = as_of.toordinal() if hasattr(as_of, "toordinal") else date.fromisoformat(str(as_of)).toordinal()
    offset = ((day - date(2026, 11, 11).toordinal()) * limit) % len(urls)
    return [urls[(offset + index) % len(urls)]
            for index in range(min(limit, len(urls)))]


def inspection_targets(page_rows, limit=20, core_query_pages=None, as_of=None):
    """Inspect core canonical URLs first, then target-query landing pages.

    Preserve a small quota for freshly published articles and for other
    Search Console page-impression evidence. Search Analytics rows may
    contain legacy .html URLs, which must be inspected alongside canonical
    variants when capacity permits.
    """
    from urllib.parse import urlsplit
    urls = list(INSPECT_URLS[:limit])
    seen = set(urls)

    def append_observed(observed):
        parts = urlsplit(str(observed).strip())
        if (parts.scheme != 'https' or parts.netloc != 'linkwiki.info'
                or parts.query or parts.fragment):
            return
        path = parts.path.rstrip('/')
        candidates = [str(observed).strip()]
        if path == '/index.html':
            candidates.insert(0, 'https://linkwiki.info/')
        elif path.endswith('.html'):
            candidates.insert(0, 'https://linkwiki.info' + path[:-5])
        for candidate in candidates:
            if candidate not in seen and len(urls) < limit:
                urls.append(candidate)
                seen.add(candidate)

    # True target-query landing URLs take precedence over unrelated
    # page-impression rows; the three intended queries may point to
    # unexpected internal pages even when the homepage ranks poorly.
    for row in sorted(core_query_pages or [],
                      key=lambda item: -int(item.get('impressions', 0))):
        keys = row.get('keys') or []
        if len(keys) < 2 or ''.join(str(keys[0]).split()) not in CORE_KEYWORDS:
            continue
        append_observed(keys[1])

    # Scheduled reports keep two available slots for older real guides.
    # The original ordering could exhaust the 20-URL inspection cap before
    # reaching the rotating section; reserve actual slots after exact-query
    # landings while retaining those high-priority observed pages.
    if as_of is not None and limit >= len(INSPECT_URLS) + 2:
        for url in rotating_inspection_urls(as_of, limit=2):
            if url not in seen and len(urls) < limit:
                urls.append(url)
                seen.add(url)

    # Inspect actually observed legacy .html URLs with their canonical
    # counterparts before spending the remaining quota on newly published
    # articles. Otherwise a content batch can evict real Google redirect
    # evidence from the limited URL Inspection queue.
    for row in sorted(page_rows, key=lambda item: -int(item.get('impressions', 0))):
        keys = row.get('keys') or []
        if keys and urlsplit(str(keys[0])).path.endswith('.html'):
            append_observed(keys[0])

    # Prioritize three distinct directory-task guides even when same-day
    # filename ordering would omit them from a generic newest-three sample.
    # Exact-query landing pages above always take precedence.
    for url in directory_intent_inspection_urls():
        if url not in seen and len(urls) < limit:
            urls.append(url)
            seen.add(url)

    # Keep newly published articles represented, independent of traffic.
    for url in recent_published_post_urls():
        if url not in seen and len(urls) < limit:
            urls.append(url)
            seen.add(url)

    for row in sorted(page_rows, key=lambda item: -int(item.get('impressions', 0))):
        keys = row.get('keys') or []
        if keys:
            append_observed(keys[0])
    return urls


def list_submitted_sitemaps(token, property_url):
    """Read actual GSC sitemap registration/processing state; no submission."""
    endpoint = ('https://www.googleapis.com/webmasters/v3/sites/' +
                quote(property_url, safe='') + '/sitemaps')
    request = Request(endpoint, headers={'Authorization': f'Bearer {token}',
                                         'Accept': 'application/json'}, method='GET')
    with urlopen(request, timeout=25) as response:
        data = json.load(response)
    return data.get('sitemap', [])


def format_sitemap_health(sitemaps, error=''):
    """Distinguish Google-submitted sitemap from robots.txt discovery hint."""
    source = 'https://linkwiki.info/sitemap.xml'
    matched = next((row for row in sitemaps if row.get('path') == source), None)
    lines = ['', '## Google Search Console 사이트맵 제출·처리 상태', '']
    if error:
        lines.append('- 조회 실패 · 제출 여부 확인 불가: ' + str(error))
    elif matched is None:
        lines.extend([
            '- **Search Console에 기본 사이트맵 제출 기록이 확인되지 않았습니다.**',
            '- robots.txt에 Sitemap 주소가 있어도 Search Console 제출 이력을 뜻하지 않습니다.',
            '- 우선 제출 여부와 등록 속성(sc-domain:linkwiki.info)을 확인하고, '
            '미제출이면 Google Search Console 사이트맵에 ' + source + ' 을 등록하세요.',
        ])
    else:
        submitted = str(matched.get('lastSubmitted') or '정보 없음')
        downloaded = str(matched.get('lastDownloaded') or '아직 없음')
        pending = bool(matched.get('isPending', False))
        warning = int(matched.get('warnings') or 0)
        errors = int(matched.get('errors') or 0)
        lines.extend([
            '- 기본 사이트맵 Search Console 제출 기록: 확인',
            '- 제출: ' + submitted + ' · Google 마지막 다운로드: ' + downloaded,
            '- 처리 대기: ' + ('예' if pending else '아니오') +
            ' · 오류: ' + str(errors) + ' · 경고: ' + str(warning),
        ])
        if errors > 0:
            lines.append('- **사이트맵 처리 오류를 Search Console에서 확인하세요.**')
        elif pending:
            lines.append('- **Google이 아직 사이트맵 처리를 완료하지 않았습니다.** 다운로드 기록 및 제출 상태를 확인하세요.')
        elif downloaded == '아직 없음':
            lines.append('- Google의 다운로드가 아직 확인되지 않았습니다.')
        else:
            lines.append('- 사이트맵이 제출·다운로드됐더라도 개별 URL 색인은 보장되지 않습니다.')
    lines.extend(['', '- 이 결과는 Google API에 기록된 사이트맵 정보이며, '
                  '실제 재크롤링·색인 완료를 의미하지 않습니다.', ''])
    # The site also publishes an identical v2 sitemap that may have a distinct
    # history in Search Console. Read BOTH submitted sources so a failed recent
    # sitemap.xml fetch is not mistaken for total Google sitemap blindness.
    legacy_source = 'https://linkwiki.info/sitemap-v2.xml'
    legacy = next((row for row in sitemaps if row.get('path') == legacy_source), None)
    lines.extend(['', '### 대체 사이트맵(sitemap-v2.xml) 기록', ''])
    if error:
        lines.append('- API 조회 실패 · 대체 사이트맵 처리 여부도 확인 불가')
    elif legacy is None:
        lines.append('- GSC에 대체 사이트맵 제출 기록이 없습니다.')
    else:
        last_read = str(legacy.get('lastDownloaded') or '아직 없음')
        state = str(legacy.get('lastSubmitted') or '제출 기록 시간 없음')
        errors_v2 = int(legacy.get('errors') or 0)
        warnings_v2 = int(legacy.get('warnings') or 0)
        lines.append('- 제출: ' + state + ' · 마지막 다운로드: ' + last_read)
        lines.append('- 처리 오류: ' + str(errors_v2) + ' · 경고: ' + str(warnings_v2))
        if matched is not None and not matched.get('lastDownloaded') and last_read != '아직 없음':
            lines.append('- **진단: 기본 사이트맵은 아직 다운로드되지 않았지만, 대체 사이트맵은 Google에 다운로드 기록이 있습니다.**')
            lines.append('- 두 XML은 배포 빌드에서 동일한 내용입니다. '
                         '이전 사이트맵 성공을 전체 사이트맵 인식 실패와 혼동하지 마세요.')
        if errors_v2 == 0 and last_read != '아직 없음':
            lines.append('- 대체 사이트맵의 처리 기록은 확인됐으나, 새 콘텐츠의 재크롤링·색인 성공을 의미하지 않습니다.')
    lines.append('')
    return '\n'.join(lines)


def inspect_index(token, property_url, inspection_url):
    """Read Google's indexed-version status; this does not request indexing."""
    request = Request(
        'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect',
        json.dumps({'inspectionUrl': inspection_url, 'siteUrl': property_url,
                    'languageCode': 'ko-KR'}).encode('utf-8'),
        {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST')
    with urlopen(request, timeout=20) as response:
        data = json.load(response)
    state = data.get('inspectionResult', {}).get('indexStatusResult', {})
    return {'url': inspection_url, 'verdict': state.get('verdict', 'UNKNOWN'),
            'coverage': state.get('coverageState', '정보 없음'),
            'last_crawl': state.get('lastCrawlTime', ''),
            'google_canonical': state.get('googleCanonical', ''),
            'user_canonical': state.get('userCanonical', ''),
            'robots_state': state.get('robotsTxtState', ''),
            'indexing_state': state.get('indexingState', ''),
            'fetch_state': state.get('pageFetchState', ''),
            'sitemaps': state.get('sitemap', []),
            'referring_urls': state.get('referringUrls', [])}


def technical_index_obstacles(item):
    """Classify explicit Google inspection blockers, not inferred SEO quality."""
    if not item:
        return []
    issues = []
    robots = str(item.get('robots_state') or '')
    indexing = str(item.get('indexing_state') or '')
    fetched = str(item.get('fetch_state') or '')
    declared = str(item.get('user_canonical') or '')
    selected = str(item.get('google_canonical') or '')
    if robots == 'DISALLOWED':
        issues.append('Google robots.txt 차단 확인')
    if indexing == 'BLOCKED_BY_META_TAG':
        issues.append('Google HTML noindex 확인')
    if indexing == 'BLOCKED_BY_HTTP_HEADER':
        issues.append('Google HTTP X-Robots-Tag noindex 확인')
    if fetched and fetched not in ('SUCCESSFUL', 'PAGE_FETCH_STATE_UNSPECIFIED'):
        issues.append('Google 페이지 가져오기: ' + fetched)
    if declared and selected and declared != selected:
        issues.append('사이트 지정 canonical과 Google 선택 canonical 불일치')
    return issues


def technical_index_diagnostic(rows):
    """Explain concrete blocking signals for priority pages without inventing causes."""
    priority = ('https://linkwiki.info/directory',
                'https://linkwiki.info/', 'https://linkwiki.info/categories/')
    by_url = {str(row.get('url', '')): row for row in rows}
    lines = ['', '### 핵심 URL 기술적 색인 차단 진단', '',
             '| URL | robots.txt | 색인 허용 상태 | Google 페이지 가져오기 | 사이트 canonical | Google canonical |',
             '|---|---|---|---|---|---|']
    priority += tuple('https://linkwiki.info/categories/' + slug for slug in (
        'community', 'korean', 'comics-directory', 'webtoon',
        'ai', 'search', 'sports', 'video'))
    safe = lambda value: str(value or '정보 없음').replace('|', '%7C').replace('\n', ' ')
    for url in priority:
        row = by_url.get(url)
        if row is None:
            lines.append('| ' + safe(url) + ' | ' + ' | '.join(['미조회'] * 5) + ' |')
            continue
        lines.append('| ' + ' | '.join(safe(value) for value in (
            url, row.get('robots_state'), row.get('indexing_state'),
            row.get('fetch_state'), row.get('user_canonical'),
            row.get('google_canonical'))) + ' |')
        for issue in technical_index_obstacles(row):
            lines.append('- ' + url + ': ' + issue)
        coverage = str(row.get('coverage') or '').casefold()
        no_crawl_data = (
            ('알려지지' in coverage or 'unknown to google' in coverage
             or 'url is unknown' in coverage)
            or (not row.get('last_crawl')
                and str(row.get('robots_state') or '') in
                ('', 'ROBOTS_TXT_STATE_UNSPECIFIED')
                and str(row.get('fetch_state') or '') in
                ('', 'PAGE_FETCH_STATE_UNSPECIFIED'))
        )
        if no_crawl_data:
            lines.append('- ' + url + ': Google 크롤링·색인 기술 정보 미제공. '
                         '차단이 없다고 판단할 수 없습니다. 공개 HTML 내부 링크와 '
                         'Google 발견 경로를 별도로 검토하세요.')
        elif (not technical_index_obstacles(row)
              and row.get('verdict') not in ('PASS', None, 'UNKNOWN')):
            lines.append('- ' + url + ': 저장된 크롤링 정보에서 명시적 차단은 보이지 않습니다. '
                         '콘텐츠 품질이 미색인 원인이라는 뜻은 아닙니다.')
    lines.extend(['', '- Google URL Inspection API의 색인 저장본 기준으로, '
                  '현재 실시간 HTTP 상태와 다를 수 있습니다.',
                  '- sitemap 및 발견 경로는 Google API에서 일부만 제공할 수 있습니다.', ''])
    return '\n'.join(lines)


def crawl_after_significant_change(rows, changes):
    """Compare Google index-copy crawl date with independently recorded edit date.

    Same-date crawls are ambiguous because significant edits record calendar dates,
    not timestamps. Missing last-crawl is unknown, not proof of no discovery.
    """
    inspected = {str(row.get('url', '')): row for row in rows}
    out = ['', '### 실제 콘텐츠 변경 이후 Google 재크롤링 확인', '',
           '| 핵심 URL | 최종 콘텐츠 변경일 | Google 마지막 크롤링 | 판정 |',
           '|---|---|---|---|']
    paths = ('/', '/directory', '/categories/') + tuple(
        '/categories/' + slug for slug in (
            'community', 'korean', 'comics-directory', 'webtoon',
            'ai', 'search', 'sports', 'video'))
    for path in paths:
        changed = changes.get(path)
        if not changed:
            continue
        url = 'https://linkwiki.info' + path
        item = inspected.get(url)
        crawled = str((item or {}).get('last_crawl') or '')
        if not item:
            verdict = '조회 결과 없음 · 재크롤링 여부 불명'
        elif not crawled:
            verdict = '크롤링 시점 미제공 · 재크롤링 여부 불명'
        else:
            try:
                crawl_day = date.fromisoformat(crawled[:10])
                changed_day = date.fromisoformat(changed)
            except ValueError:
                verdict = '날짜 형식 오류 · 판정 불가'
            else:
                if crawl_day < changed_day:
                    verdict = '최신 수정 이전 크롤링 · 변경 후 재크롤링 미확인'
                elif crawl_day == changed_day:
                    verdict = '같은 날짜 크롤링 · 수정 전후 순서 미확정'
                else:
                    verdict = '콘텐츠 변경 날짜 이후 재크롤링 확인'
        out.append('| ' + ' | '.join(str(value).replace('|', '%7C') for value
                                   in (url, changed, crawled or '-', verdict)) + ' |')
    out.extend(['', '- 변경일은 실제로 수정한 핵심 페이지에만 적용하며 빌드일과 무관합니다.',
                '- 재크롤링 확인은 색인 등록 또는 검색 순위 개선의 증거가 아닙니다.', ''])
    return '\n'.join(out)


def priority_index_checks(rows):
    """Summarize Google-reported status for the homepage and core directory.

    Only inspect observed API results. Missing API rows are *unknown*, not
    evidence that Google has not discovered or indexed an address.
    """
    high_priority = (
        ('https://linkwiki.info/directory', '핵심 주소모음 목록'),
        ('https://linkwiki.info/', '홈페이지'),
        ('https://linkwiki.info/categories/', '카테고리 허브'),
    )
    by_url = {str(item.get('url', '')): item for item in rows}
    output = ['', '### 핵심 URL 색인 우선 점검', '',
              '| URL | 역할 | 결과 | Google 선택 정규 URL | 다음 조치 |',
              '|---|---|---|---|---|']
    for url, role in high_priority:
        item = by_url.get(url)
        if not item:
            verdict, canonical = '조회 결과 없음', '-'
            action = 'URL Inspection API 재조회 및 접근 권한 확인'
        else:
            verdict = str(item.get('verdict') or 'UNKNOWN')
            canonical = str(item.get('google_canonical') or '-')
            coverage = str(item.get('coverage') or '')
            obstacles = technical_index_obstacles(item)
            if obstacles:
                action = '; '.join(obstacles)
            elif verdict == 'PASS' and canonical != '-' and canonical != url:
                action = 'Google 선택 정규 URL과 사이트 canonical 차이 검토'
            elif verdict == 'PASS':
                action = '검색 실적과 검색어별 노출 URL 확인'
            elif 'unknown to google' in coverage.casefold() or '알려지지' in coverage:
                action = '사이트맵 제출·홈페이지 내부 링크·실제 HTTP 접근 확인'
            elif 'not indexed' in coverage.casefold() or '색인이 생성되지' in coverage:
                action = '페이지 고유 가치·중복 내용·canonical 검토'
            else:
                action = '색인 상세 상태 및 마지막 크롤링 확인'
        safe = lambda value: str(value).replace('|', '%7C').replace('\n', ' ')
        output.append('| ' + ' | '.join(map(safe, (url, role, verdict, canonical, action))) + ' |')
    output.extend(['', '- 위 점검은 API 조회 시점의 Google 색인 저장본에 한정됩니다.',
                   '- 조회 결과가 없다는 사실은 Google 미발견 또는 미색인을 뜻하지 않습니다.', ''])
    return '\n'.join(output)


def compare_search_visibility_with_inspection(page_rows, inspection_rows, end_date):
    """Surface disagreement between two GSC products, not imagined penalties.

    Search Analytics covers observed search appearances over a past window.
    URL Inspection returns Google's latest exposed stored status. Neither
    proves the other is wrong; dates can lag independently.
    """
    if not inspection_rows:
        return []
    inspected = {str(x.get("url") or ""): x for x in inspection_rows}
    findings = []
    for row in page_rows or []:
        keys = row.get("keys") or []
        if not keys:
            continue
        url = str(keys[0])
        item = inspected.get(url)
        impressions = int(row.get("impressions") or 0)
        if item is None or impressions <= 0 or item.get("verdict") == "PASS":
            continue
        findings.append({
            "url": url, "impressions": impressions,
            "clicks": int(row.get("clicks") or 0),
            "inspection": str(item.get("coverage") or "정보 없음"),
            "last_crawl": str(item.get("last_crawl") or ""),
            "end_date": str(end_date),
        })
    return sorted(findings, key=lambda x: (-x["impressions"], x["url"]))


def format_search_visibility_inspection_conflicts(page_rows, inspection_rows,
                                                 end_date, inspection_error=''):
    lines = [
        "", "### 검색 실적과 URL 검사 상태 간의 시점 차이", "",
        "- 검색 성과는 기간 중 실제 검색 노출 기록이며 URL 검사는 Google이 제공하는 "
        "별도 저장 상태입니다. 두 데이터가 서로 다른 시점에 갱신될 수 있습니다.",
        "- 아래에 표시된 페이지를 '검색에 전혀 나타나지 않는 URL'로 단정하지 마세요.",
        "| 노출 URL | 조회 기간 노출 | 클릭 | URL 검사 저장 상태 | 마지막 기록된 크롤링 |",
        "|---|---:|---:|---|---|",
    ]
    if inspection_error:
        return "\n".join(lines + [
            "| URL 검사 조회 실패 | - | - | " + str(inspection_error) + " | - |",
            "",
        ])
    conflicts = compare_search_visibility_with_inspection(
        page_rows, inspection_rows, end_date)
    if not conflicts:
        lines.append("| 불일치 관측 없음 | - | - | - | - |")
    for entry in conflicts:
        safe = lambda value: str(value).replace("|", "%7C").replace("\n", " ")
        lines.append("| " + " | ".join(safe(x) for x in (
            entry["url"], entry["impressions"], entry["clicks"],
            entry["inspection"], entry["last_crawl"] or "-")) + " |")
    lines += ["", "- 이 불일치는 Google의 수동 조치나 품질 평가 확정 근거가 아닙니다.", ""]
    return "\n".join(lines)


def format_google_discovery_evidence(rows, error=''):
    """Show Google's reported discovery hints without inferring non-discovery.

    The URL Inspection API may omit sitemaps and referring pages even for an
    indexed URL. An empty array is not proof that no discovery route exists.
    """
    priority = (
        "https://linkwiki.info/directory",
        "https://linkwiki.info/",
        "https://linkwiki.info/categories/",
    )
    observed = {str(row.get("url", "")): row for row in rows}
    lines = [
        "", "### Google이 보고한 핵심 URL 발견 경로", "",
        "- 사이트맵·참조 페이지는 URL Inspection API가 보고한 항목만 표시합니다.",
        "- 정보 미제공은 발견 경로가 없다는 뜻이 아닙니다.",
        "| URL | 보고된 사이트맵 | 보고된 참조 페이지 |",
        "|---|---|---|",
    ]

    def display(values):
        if not isinstance(values, list) or not values:
            return "정보 미제공"
        actual = [str(value).replace("|", "%7C").replace("\n", " ")
                  for value in values if isinstance(value, str) and value.strip()]
        return ", ".join(actual[:3]) + (f" 외 {len(actual) - 3}개" if len(actual) > 3 else "") if actual else "정보 미제공"

    for url in priority:
        row = observed.get(url)
        if row is None:
            reason = "조회 실패·일부 미완료" if error else "URL 검사 미수행"
            status, source = reason, reason
        else:
            status = display(row.get("sitemaps"))
            source = display(row.get("referring_urls"))
        lines.append(f"| {url} | {status} | {source} |")
    return "\n".join(lines)


def format_index_inspection(rows, error=''):
    lines = ['', '## Google 색인 상태 확인 (Google 색인에 저장된 버전)', '',
             '- URL Inspection API 결과이며 실시간 접속 상태나 색인 신청 결과가 아닙니다.',
             '| URL | 판정 | 상태 | 마지막 크롤링 | Google 선택 정규 URL |',
             '|---|---|---|---|---|']
    for row in rows:
        safe = lambda value: str(value).replace('|', '%7C').replace('\n', ' ')
        lines.append('| ' + ' | '.join(safe(row.get(key, '')) for key in
                     ('url', 'verdict', 'coverage', 'last_crawl', 'google_canonical')) + ' |')
    if rows:
        indexed = sum(row.get('verdict') == 'PASS' for row in rows)
        def coverage_kind(row):
            state = str(row.get('coverage', '')).casefold()
            if ('알려지지' in state or 'unknown to google' in state
                    or 'url is unknown' in state):
                return 'unknown'
            if (('크롤링됨' in state or 'crawled' in state)
                    and ('색인이 생성되지' in state or 'not indexed' in state)):
                return 'crawled_not_indexed'
            return 'other'

        unknown = [row for row in rows if coverage_kind(row) == 'unknown']
        crawled = [row for row in rows if coverage_kind(row) == 'crawled_not_indexed']
        lines.extend(['', '### 점검한 URL 중 색인 우선 조치',
                      f'- 검사한 URL: {len(rows)}개 · 색인 PASS: {indexed}개 · '
                      f'Google에 알려지지 않음: {len(unknown)}개 · '
                      f'크롤링 후 미색인: {len(crawled)}개',
                      '- 이 수치는 검사된 URL에 한정하며 사이트 전체의 색인 수가 아닙니다.',
                      '- 미발견 URL: 내부 링크·사이트맵·실제 접근 상태부터 점검합니다.',
                      '- 크롤링 후 미색인: 콘텐츠의 고유한 가치와 검색 의도 적합성을 검토합니다.',
                      '- 조회 결과만으로 자동 색인 신청이나 검색 순위 상승을 보장하지 않습니다.', ''])
        for row in (unknown + crawled)[:12]:
            lines.append('- ' + str(row.get('url', '')) + ' — ' +
                         str(row.get('coverage', '정보 없음')).replace('\n', ' '))
    lines.append(priority_index_checks(rows))
    lines.append(format_google_discovery_evidence(rows, error))
    lines.append(technical_index_diagnostic(rows))
    change_log = ROOT / 'seo/significant-page-updates.json'
    if change_log.is_file():
        changes = json.loads(change_log.read_text(encoding='utf-8'))
        lines.append(crawl_after_significant_change(rows, changes))
    if error:
        lines.extend(['', '색인 조회 일부 또는 전체 실패: ' + error])
    if not rows:
        lines.append('| 조회 결과 없음 | - | - | - | - |')
    return '\n'.join(lines)


CORE_KEYWORDS = ("주소모음", "링크모음", "사이트모음")

# Google Search Analytics API supports RE2 includingRegex query filters.
# A dedicated filtered request prevents the top-ranked query list from
# obscuring low-impression observations of our three target keywords.
CORE_QUERY_FILTERS = [{
    "groupType": "and",
    "filters": [{
        "dimension": "query", "operator": "includingRegex",
        "expression": r"^(주소[[:space:]]*모음|링크[[:space:]]*모음|사이트[[:space:]]*모음)$",
    }],
}]



# Search Console country codes are three-letter ISO 3166-1 alpha-3.
# Keep Korean-market measurements separate from global measurements.
KOREA_CORE_QUERY_FILTERS = [{
    "groupType": "and",
    "filters": [
        {"dimension": "query", "operator": "includingRegex",
         "expression": r"^(주소[[:space:]]*모음|링크[[:space:]]*모음|사이트[[:space:]]*모음)$"},
        {"dimension": "country", "operator": "equals", "expression": "kor"},
    ],
}]


# Broader discovery is kept separate from exact-query performance. A site can
# rank well for '주소모음 위키' yet rank poorly for the head term '주소모음'.
FAMILY_QUERY_FILTERS = [{
    "groupType": "and",
    "filters": [{
        "dimension": "query", "operator": "includingRegex",
        "expression": r"(주소[[:space:]]*모음|링크[[:space:]]*모음|사이트[[:space:]]*모음)",
    }],
}]


def core_family_keyword_rows(rows):
    """Split literal core keywords from related queries, without double counting.

    Rows may match more than one family (e.g., 주소모음 링크모음). For that
    case, assign the first family in CORE_KEYWORDS so the overall sum is
    disjoint. This is a measurement convention, not a ranking signal.
    """
    groups = {
        key: {"exact": [], "related": []} for key in CORE_KEYWORDS
    }
    for row in rows or []:
        keys = row.get("keys") or []
        if not keys:
            continue
        query = str(keys[0])
        compact = ''.join(query.split())
        matched = next((key for key in CORE_KEYWORDS if key in compact), None)
        if matched is None:
            continue
        groups[matched]["exact" if compact == matched else "related"].append(row)

    def aggregate(items):
        impressions = sum(int(row.get("impressions", 0)) for row in items)
        clicks = sum(int(row.get("clicks", 0)) for row in items)
        weighted = sum(float(row.get("position", 0)) *
                       int(row.get("impressions", 0)) for row in items)
        return {"impressions": impressions, "clicks": clicks,
                "position": round(weighted / impressions, 1) if impressions else None,
                "observed": bool(items)}

    return [{"keyword": keyword, "exact": aggregate(data["exact"]),
             "related": aggregate(data["related"])}
            for keyword, data in groups.items()]


def format_core_family_keyword_report(rows, error=''):
    lines = [
        '', '## 핵심 키워드와 연관 검색어 분리 측정', '',
        '- 정확 일치(띄어쓰기 변형 포함)와 검색어에 키워드가 포함된 '
        '연관 검색을 **별도** 집계합니다. 연관 검색 순위를 핵심 단일 키워드 '
        '순위로 해석하지 않습니다.',
        '- 두 개 이상의 핵심 표현이 한 검색어에 함께 있을 때는 '
        '주소모음 → 링크모음 → 사이트모음 순서로 한 번만 집계합니다.',
        '- 미관측은 검색어 데이터 미제공을 뜻하며 검색량 0을 보장하지 않습니다.',
        '| 핵심 표현 | 정확 검색 노출 / 클릭 / 평균 순위 | 연관 검색 노출 / 클릭 / 평균 순위 |',
        '|---|---|---|',
    ]
    if error:
        lines.append('| 조회 오류 | ' + str(error) + ' | - |')
        return '\n'.join(lines)
    def show(item):
        return (f"{item['impressions']} / {item['clicks']} / "
                f"{item['position']:.1f}" if item['observed'] and
                item['position'] is not None else '관측 없음')
    for row in core_family_keyword_rows(rows):
        lines.append(f"| {row['keyword']} | {show(row['exact'])} | {show(row['related'])} |")
    return '\n'.join(lines)


def core_keyword_rows(keyword_rows, query_page_rows=None):
    """Use observed query rows only; merge internal whitespace variants."""
    output = []
    for target in CORE_KEYWORDS:
        matched = [
            row for row in keyword_rows
            if ''.join(str((row.get("keys") or [""])[0]).split()) == target
        ]
        impressions = sum(int(row.get("impressions", 0)) for row in matched)
        clicks = sum(int(row.get("clicks", 0)) for row in matched)
        weighted = sum(float(row.get("position", 0)) * int(row.get("impressions", 0))
                       for row in matched)
        pages = sorted({
            str(row["keys"][1]) for row in (query_page_rows or [])
            if len(row.get("keys") or []) >= 2
            and ''.join(str(row["keys"][0]).split()) == target
        })
        output.append({
            "keyword": target, "impressions": impressions,
            "clicks": clicks,
            "position": round(weighted / impressions, 1) if impressions else None,
            "pages": pages, "observed": bool(matched),
        })
    return output



def core_keyword_weekly_comparison(rows, end_date):
    """Compare two disjoint seven-day windows of *observed* keyword-date rows.

    GSC may anonymize low-volume queries: missing rows are zero observed rows,
    never proof that the keyword had no real searches or Google impressions.
    Distinguish no-row from a genuine reported position.
    """
    end = date.fromisoformat(str(end_date))
    by_key = {key: {"recent": [], "previous": []} for key in CORE_KEYWORDS}
    for row in rows or []:
        keys = row.get('keys') or []
        if len(keys) < 2:
            continue
        raw_key, day_string = str(keys[0]), str(keys[1])
        key = ''.join(raw_key.split())
        if key not in by_key:
            continue
        try:
            day = date.fromisoformat(day_string)
        except ValueError:
            continue
        age = (end - day).days
        if not 0 <= age < 14:
            continue
        by_key[key]['recent' if age < 7 else 'previous'].append(row)

    def summarize(selected):
        impressions = sum(int(row.get('impressions', 0)) for row in selected)
        clicks = sum(int(row.get('clicks', 0)) for row in selected)
        weighted = sum(float(row.get('position', 0)) *
                       int(row.get('impressions', 0)) for row in selected)
        return {
            'impressions': impressions, 'clicks': clicks,
            'position': round(weighted / impressions, 1) if impressions else None,
            'observed': bool(selected),
        }

    return [
        {'keyword': key,
         'recent': summarize(windows['recent']),
         'previous': summarize(windows['previous'])}
        for key, windows in by_key.items()
    ]


def format_core_keyword_weekly_comparison(rows, end_date, error='', scope='global'):
    """Render genuine week-over-week impressions, clicks and weighted ranks."""
    lines = [
        '', ('## 대한민국 이용자 기준 최근 7일 핵심 키워드 노출 변화'
             if scope == 'korea' else
             '## 주소모음·링크모음·사이트모음 최근 7일 노출 변화'), '',
        '- Google Search Console 검색어×날짜 필터 결과만 사용합니다. '
        '브랜드 검색, 검색량 추정치, 외부 검색 API 순위는 포함하지 않습니다.',
        f'- 비교 기간: 최근 7일 {end_date} 종료 / 직전 7일은 그 이전 7일.',
        '- 데이터 없음은 GSC에 공개된 해당 검색어 행이 없다는 뜻이며 '
        '실제 노출 0회를 보장하지 않습니다.',
        '| 키워드 | 직전 7일 노출·클릭 | 최근 7일 노출·클릭 | '
        '관측 노출 변화 | 직전 평균 순위 | 최근 평균 순위 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    if error:
        lines.append('- 별도 핵심 키워드 일별 조회 실패: ' + str(error))
        lines.append('| 조회 실패 | - | - | - | - | - |')
        return '\n'.join(lines)
    for item in core_keyword_weekly_comparison(rows, end_date):
        prior, recent = item['previous'], item['recent']
        def count_text(window):
            return (f"{window['impressions']}회 · {window['clicks']}회"
                    if window['observed'] else '관측 없음')
        delta = (f"{recent['impressions'] - prior['impressions']:+d}회 (관측 기준)"
                 if prior['observed'] or recent['observed'] else '비교 불가')
        def rank_text(window):
            return f"{window['position']:.1f}위" if window['position'] is not None else '-'
        lines.append('| ' + ' | '.join((
            item['keyword'], count_text(prior), count_text(recent), delta,
            rank_text(prior), rank_text(recent)
        )) + ' |')
    lines.extend([
        '', '- 표본이 적으면 평균 순위 변화가 크게 흔들립니다. '
        '순위 변화가 없거나 검색어 행이 없다고 곧바로 개선 실패를 단정하지 않습니다.',
        '- 이 비교는 완료된 GSC 집계일 기준이며, 오늘의 실시간 검색 결과가 아닙니다.',
        ''
    ])
    return '\n'.join(lines)





def format_core_landing_page_split(query_page_rows, error=''):
    """Show which site URLs Google actually surfaced for each exact core query.

    This does not infer indexation from absence of search analytics rows.
    """
    lines = ['', '## 핵심 키워드별 실제 노출 URL 분포', '',
             '- Google Search Console 검색어×페이지 실측 데이터만 사용합니다.',
             '- 한 검색어로 여러 URL이 노출되면 페이지별 목적과 내부 링크를 검토하세요.',
             '| 키워드 | 노출 URL | 노출 | 클릭 | 평균 순위 |',
             '|---|---|---:|---:|---:|']
    if error:
        return '\n'.join(lines + ['| 조회 실패 | - | - | - | - |', '',
                                   '- 조회 오류: ' + str(error), ''])
    observed = False
    for keyword in CORE_KEYWORDS:
        matched = []
        for row in query_page_rows or []:
            keys = row.get('keys') or []
            if len(keys) < 2 or ''.join(str(keys[0]).split()) != keyword:
                continue
            url = str(keys[1])
            if not url.startswith('https://linkwiki.info/'):
                continue
            matched.append(row)
        for row in sorted(matched, key=lambda x: -int(x.get('impressions', 0)))[:10]:
            observed = True
            impressions = int(row.get('impressions', 0))
            position = (f"{float(row.get('position', 0)):.1f}" if impressions else '-')
            url = str(row['keys'][1]).replace('|', '%7C')
            lines.append(f"| {keyword} | {url} | {impressions} | "
                         f"{int(row.get('clicks', 0))} | {position} |")
    if not observed:
        lines.append('| 관측된 검색어·페이지 조합 없음 | - | - | - | - |')
    lines.extend(['', '- 관측된 URL이 여러 개여도 자동으로 키워드 잠식이라고 단정하지 않습니다.',
                  '- 검색어가 익명 처리되거나 노출이 적으면 이 표에 표시되지 않을 수 있습니다.', ''])
    return '\n'.join(lines)


def brand_vs_nonbrand_rows(keyword_rows):
    """Separate observed branded queries without extrapolating anonymized traffic."""
    result = {"브랜드 검색": {"impressions": 0, "clicks": 0, "weighted": 0.0},
              "일반 검색": {"impressions": 0, "clicks": 0, "weighted": 0.0}}
    for row in keyword_rows:
        keys = row.get("keys") or []
        if not keys:
            continue
        normalized = re.sub(r"[\s\W_]+", "", str(keys[0]).casefold())
        group = "브랜드 검색" if normalized in ("링크위키", "linkwiki") else "일반 검색"
        impressions = int(row.get("impressions", 0))
        result[group]["impressions"] += impressions
        result[group]["clicks"] += int(row.get("clicks", 0))
        result[group]["weighted"] += float(row.get("position", 0)) * impressions
    return [
        {"name": name, "impressions": values["impressions"],
         "clicks": values["clicks"],
         "position": round(values["weighted"] / values["impressions"], 1)
         if values["impressions"] else None}
        for name, values in result.items()
    ]


def format_report(keyword_rows, page_rows, start_date, end_date, property_url,
                  date_rows=None, query_page_rows=None, focused_keyword_rows=None,
                  focused_query_page_rows=None, focused_error=''):
    lines = ['# 링크위키 Search Console 실적', '',
             f'- 속성: `{property_url}`', f'- 조회 기간: {start_date} ~ {end_date}',
             '- 데이터: Google Search Console API. 검색량이나 실시간 순위가 아닙니다.', '']
    # Date-based totals include impressions from anonymized query rows.
    daily = sorted(date_rows or [], key=lambda row: (row.get('keys') or [''])[0])
    if daily:
        clicks = sum(int(row.get('clicks', 0)) for row in daily)
        impressions = sum(int(row.get('impressions', 0)) for row in daily)
        ctr = clicks / impressions * 100 if impressions else 0
        lines.extend([
            '## 전체 검색 성과 (날짜별 합계)', '',
            f'- 노출: {impressions:,}회 · 클릭: {clicks:,}회 · CTR: {ctr:.1f}%',
            '- 검색어 표와 전체 합계는 익명 검색어 처리로 차이가 날 수 있습니다.', '',
        ])
    else:
        lines.extend(['## 전체 검색 성과', '', '날짜별 검색 성과 데이터 없음', ''])
    if not keyword_rows and page_rows:
        lines.extend(['', '검색어 행은 0개지만 페이지별 데이터가 있습니다. 검색어 익명 처리나 집계 기준 차이일 수 있으므로 노출 0회로 해석하지 마세요.', ''])
    # Compare true calendar weeks, not the last fourteen non-empty API rows.
    # Search Console can omit zero-activity days, especially on new properties.
    window_end = date.fromisoformat(str(end_date))
    if (date.fromisoformat(str(start_date)) <= window_end - timedelta(days=13)):
        by_day = {str((row.get('keys') or [''])[0]): row for row in daily}
        def calendar_week_totals(week_end):
            dates = [(week_end - timedelta(days=offset)).isoformat() for offset in range(7)]
            return (
                sum(int(by_day.get(day, {}).get('impressions', 0)) for day in dates),
                sum(int(by_day.get(day, {}).get('clicks', 0)) for day in dates),
            )
        recent_impressions, recent_clicks = calendar_week_totals(window_end)
        previous_impressions, previous_clicks = calendar_week_totals(window_end - timedelta(days=7))
        lines.extend(['', '## 최근 7일과 직전 7일 비교', '',
                      f'- 최근 7일: 노출 {recent_impressions:,}회 · 클릭 {recent_clicks:,}회',
                      f'- 직전 7일: 노출 {previous_impressions:,}회 · 클릭 {previous_clicks:,}회',
                      '- 조회 종료일 기준 연속된 7일씩 비교하며, 활동이 없는 날짜는 0회로 계산합니다.', ''])
    lines.extend(['', '## 브랜드 검색과 일반 검색 (공개된 검색어 기준)', '',
                  '- 비공개·익명 검색어는 포함되지 않으므로 전체 노출/클릭 합계와 다를 수 있습니다.',
                  '- 일반 검색에는 주소모음·링크모음·사이트모음 및 브랜드명이 아닌 검색어가 포함됩니다.',
                  '| 구분 | 확인된 노출 | 클릭 | 평균 순위 |',
                  '|---|---:|---:|---:|'])
    for group in brand_vs_nonbrand_rows(keyword_rows):
        position = group["position"] if group["position"] is not None else '-'
        lines.append(f'| {group["name"]} | {group["impressions"]} | '
                     f'{group["clicks"]} | {position} |')
    lines.extend(['', '## 검색어 상위 30개', '',
                  '| 검색어 | 노출 | 클릭 | CTR | 평균 순위 |',
                  '|---|---:|---:|---:|---:|'])
    for row in keyword_rows[:30]:
        key = str((row.get('keys') or [''])[0]).replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {key} | {int(row.get('impressions', 0))} | {int(row.get('clicks', 0))} | "
                     f"{row.get('ctr', 0)*100:.1f}% | {row.get('position', 0):.1f} |")
    if not keyword_rows:
        lines.append('| 데이터 없음 | - | - | - | - |')
    lines.extend(['', '## 핵심 목표 키워드 3종 실적', '',
                  '- 주소모음·링크모음·사이트모음과 띄어쓰기 변형의 실제 조회 결과입니다.',
                  '- 검색어가 제공되지 않으면 순위를 추정하지 않습니다. 평균 순위는 노출수 가중값입니다.',
                  '| 키워드 | 노출 | 클릭 | 평균 순위 | 실제 노출 페이지 |',
                  '|---|---:|---:|---:|---|'])
    if focused_error:
        lines.append('- 별도 핵심 키워드 조회 실패: ' + focused_error)
    source_keywords = (focused_keyword_rows if focused_keyword_rows is not None
                       else keyword_rows)
    source_pages = (focused_query_page_rows if focused_query_page_rows is not None
                    else query_page_rows)
    for core in core_keyword_rows(source_keywords, source_pages):
        if not core["observed"]:
            lines.append(f'| {core["keyword"]} | 데이터 없음 | - | - | - |')
            continue
        landing = ', '.join(core["pages"][:3]).replace('|', '%7C') if core["pages"] else '페이지 쌍 데이터 없음'
        lines.append(f'| {core["keyword"]} | {core["impressions"]} | {core["clicks"]} | '
                     f'{core["position"] if core["position"] is not None else "-"} | {landing} |')
    # Work queue: observed searches already close enough to deserve targeted improvement.
    # Thresholds prevent one-off low-volume rows from dominating the report.
    opportunities = sorted(
        (row for row in keyword_rows
         if int(row.get('impressions', 0)) >= 3
         and 7 <= float(row.get('position', 0)) <= 30),
        key=lambda row: (-int(row.get('impressions', 0)), float(row.get('position', 99)))
    )[:15]
    lines.extend(['', '## 먼저 개선할 연관 검색어 후보 (실제 노출 기반)', '',
                  '- 노출 3회 이상, 평균 순위 7~30위인 검색어를 노출수 순서로 표시합니다.',
                  '- 이 표는 검색량·난도 추정이 아니라 현재 속성에서 관측한 실적입니다.', '',
                  '| 검색어 | 노출 | 클릭 | 평균 순위 |',
                  '|---|---:|---:|---:|'])
    for row in opportunities:
        key = str((row.get('keys') or [''])[0]).replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {key} | {int(row.get('impressions', 0))} | "
                     f"{int(row.get('clicks', 0))} | {float(row.get('position', 0)):.1f} |")
    if not opportunities:
        lines.append('| 조건에 맞는 검색어 없음 (또는 검색어 데이터 미제공) | - | - | - |')
    # Connect each opportunity to the landing page Google actually displayed.
    # Without query+page pairs a query-level average can hide the wrong target URL.
    candidates = sorted(
        (row for row in (query_page_rows or [])
         if len(row.get('keys') or []) >= 2
         and int(row.get('impressions', 0)) >= 3
         and 7 <= float(row.get('position', 0)) <= 30),
        key=lambda row: (-int(row.get('impressions', 0)), float(row.get('position', 99)))
    )[:20]
    lines.extend(['', '## 검색어별 실제 노출 페이지 (수정 대상)', '',
                  '- 검색어와 노출 URL이 함께 관측된 경우만 표시합니다. 한 검색어에 여러 페이지가 나올 수 있습니다.',
                  '| 검색어 | 노출 URL | 노출 | 클릭 | 평균 순위 |',
                  '|---|---|---:|---:|---:|'])
    for row in candidates:
        keys = row['keys']
        query = str(keys[0]).replace('|', '\\|').replace('\n', ' ')
        page = str(keys[1]).replace('|', '%7C')
        lines.append(f"| {query} | {page} | {int(row.get('impressions', 0))} | "
                     f"{int(row.get('clicks', 0))} | {float(row.get('position', 0)):.1f} |")
    if not candidates:
        lines.append('| 검색어·페이지 쌍의 개선 후보 없음 | - | - | - | - |')
    lines.extend(['', '## 페이지 상위 30개', '', '| URL | 노출 | 클릭 | 평균 순위 |',
                  '|---|---:|---:|---:|'])
    for row in page_rows[:30]:
        key = str((row.get('keys') or [''])[0]).replace('|', '%7C')
        lines.append(f"| {key} | {int(row.get('impressions', 0))} | "
                     f"{int(row.get('clicks', 0))} | {row.get('position', 0):.1f} |")
    if not page_rows:
        lines.append('| 데이터 없음 | - | - | - |')
    # Page-level improvements still work when Google anonymizes every query.
    page_opportunities = sorted(
        (row for row in page_rows
         if int(row.get('impressions', 0)) >= 3
         and 7 <= float(row.get('position', 0)) <= 50),
        key=lambda row: (-int(row.get('impressions', 0)), float(row.get('position', 99)))
    )[:15]
    lines.extend(['', '## 노출 페이지 우선 개선 후보 (검색어 비공개 시에도 사용)', '',
                  '- 검색어 행이 없어도 실제 노출 페이지의 평균 순위와 노출수를 기준으로 판단합니다.',
                  '- 평균 순위 7~50위, 노출 3회 이상인 페이지를 노출수 순으로 정리합니다.',
                  '| 페이지 URL | 노출 | 클릭 | 평균 순위 |',
                  '|---|---:|---:|---:|'])
    for row in page_opportunities:
        page = str((row.get('keys') or [''])[0]).replace('|', '%7C')
        lines.append(f"| {page} | {int(row.get('impressions', 0))} | "
                     f"{int(row.get('clicks', 0))} | {float(row.get('position', 0)):.1f} |")
    if not page_opportunities:
        lines.append('| 조건에 맞는 페이지 없음 | - | - | - |')
    if daily:
        lines.extend(['', '## 최근 날짜별 추세', '',
                      '| 날짜 | 노출 | 클릭 | 평균 순위 |',
                      '|---|---:|---:|---:|'])
        for row in daily[-14:]:
            day = str((row.get('keys') or [''])[0])
            lines.append(f"| {day} | {int(row.get('impressions', 0))} | "
                         f"{int(row.get('clicks', 0))} | {row.get('position', 0):.1f} |")
    lines.extend(['', '※ 데이터 집계 지연과 API 상위 행 제한으로 전체 실적과 다를 수 있습니다.', ''])
    return '\n'.join(lines)



def collect_index_inspections(token, property_url, urls, inspector=None):
    """Keep checking after URL-specific failures, stop on auth/quota failures.

    Errors are reported as unknown inspection results, never as not indexed.
    """
    inspector = inspector or inspect_index
    results = []
    errors = []
    for url in urls:
        try:
            results.append(inspector(token, property_url, url))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as error:
            status = error.code if isinstance(error, HTTPError) else None
            issue = f"{url}: {type(error).__name__}"
            if status is not None:
                issue += f" (HTTP {status})"
            errors.append(issue)
            # Authentication, quota, and backend outages commonly affect the
            # whole property. Avoid exhausting further API calls in those cases.
            if status in (401, 403, 429, 500, 502, 503, 504):
                break
    return results, "; ".join(errors)



def format_core_keyword_index_alignment(focused_pages, inspections, error=''):
    """Tie exact target-query landing pages to Google stored index status.

    This is a prioritization aid, not an automatic diagnosis of SEO quality.
    A query-page impression and a non-PASS inspection may coexist because
    Search Analytics and URL Inspection cover different times.
    """
    by_url = {str(item.get('url', '')): item for item in inspections}
    lines = [
        '', '## 핵심 키워드 실제 노출 페이지와 색인 상태 연결', '',
        '- 정확 검색어별 Search Console 노출 URL을 URL 검사 저장 상태와 나란히 봅니다.',
        '- 노출된 적이 있는 URL을 색인 상태만으로 검색 미노출이라고 단정하지 않습니다.',
        '| 검색어 | 실제 노출 페이지 | 노출 | Google URL 검사 | 우선 확인할 작업 |',
        '|---|---|---:|---|---|',
    ]
    if error:
        return '\n'.join(lines + ['| 조회 실패 | - | - | - | API 조회 상태 확인 |', ''])
    matched = []
    for row in focused_pages or []:
        keys = row.get('keys') or []
        if len(keys) < 2:
            continue
        query = ''.join(str(keys[0]).split())
        url = str(keys[1])
        if query not in CORE_KEYWORDS or not url.startswith('https://linkwiki.info/'):
            continue
        matched.append((query, url, int(row.get('impressions') or 0)))
    for query, url, impressions in sorted(matched, key=lambda x: (-x[2], x[0], x[1]))[:30]:
        inspection = by_url.get(url)
        if inspection is None:
            status = '미조회'
            next_step = '해당 노출 URL을 URL 검사 대상으로 추가'
        else:
            status = str(inspection.get('coverage') or inspection.get('verdict') or '정보 없음')
            obstacles = technical_index_obstacles(inspection)
            if obstacles:
                next_step = '; '.join(obstacles)
            elif inspection.get('verdict') == 'PASS':
                next_step = '해당 URL의 검색 의도·제목·콘텐츠 유용성 점검'
            elif '색인이 생성되지' in status or 'not indexed' in status.casefold():
                next_step = '변경 후 재크롤링 날짜·고유 콘텐츠·중복 여부 검토'
            else:
                next_step = '마지막 크롤링·발견 경로를 확인하고 결과 갱신 대기'
        safe = lambda value: str(value).replace('|', '%7C').replace('\n', ' ')
        lines.append('| ' + ' | '.join(map(safe, (
            query, url, impressions, status, next_step))) + ' |')
    if not matched:
        lines.append('| 정확 검색어·페이지 조합 관측 없음 | - | - | - | 검색어 데이터 공개 여부 확인 |')
    lines.extend([
        '', '- 핵심 키워드가 발견되지 않아도 사이트 전체가 색인되지 않았다는 뜻은 아닙니다.',
        '- Google에 마지막으로 저장된 검사 결과는 현재 공개 HTML과 다를 수 있습니다.',
        '- 이 표만으로 순위 상승이나 색인 성공을 주장할 수 없습니다.', '',
    ])
    return '\n'.join(lines)



LONG_TAIL_GUIDES = (
    ('정부24·국민신문고', 'seo-20261111-gov24-epeople-complaint-certificate'),
    ('홈택스·위택스', 'seo-20261111-tax-hometax-wetax-difference'),
    ('공공데이터포털·KOSIS', 'seo-20261111-public-data-vs-kosis-usage'),
    ('해외 한인 생활정보', 'seo-20261110-overseas-korean-community-guide'),
    ('국내 웹툰 플랫폼', 'seo-20261110-korean-webtoon-platform-guide'),
    ('주소모음 검색 실전', 'seo-20261111-address-directory-search-examples'),
    ('두 사이트 비교', 'seo-20261028-2a8841090c'),
)


def korea_guide_query_filters():
    slugs = '|'.join(re.escape(slug) for _, slug in LONG_TAIL_GUIDES)
    return [{'groupType': 'and', 'filters': [
        {'dimension': 'country', 'operator': 'equals', 'expression': 'kor'},
        {'dimension': 'page', 'operator': 'includingRegex',
         'expression': rf'^https://linkwiki[.]info/blog/({slugs})/$'},
    ]}]


def format_korea_guide_queries(rows, end, error=''):
    current = end - timedelta(days=6)
    previous = end - timedelta(days=13)
    lines = [
        '', '', '## 대한민국 검색어별 비교 가이드 실적', '',
        f'직전 7일 {previous}~{current - timedelta(days=1)} / 최근 7일 {current}~{end}.',
        'Google이 제공한 검색어 행을 가이드마다 최대 5개 표시합니다. '
        '미관측은 검색량 0이나 미색인을 뜻하지 않습니다.', '',
    ]
    if error:
        return '\n'.join(lines + [f'조회 실패: {error}', ''])
    by_page = {}
    for row in rows:
        keys = row.get('keys', [])
        if len(keys) != 3 or not previous.isoformat() <= keys[2] <= end.isoformat():
            continue
        query, page, day = keys
        impressions = int(row.get('impressions', 0))
        if impressions <= 0:
            continue
        period = int(day >= current.isoformat())
        totals = by_page.setdefault(page, {}).setdefault(query, [[0, 0, 0.0], [0, 0, 0.0]])
        totals[period][0] += impressions
        totals[period][1] += int(row.get('clicks', 0))
        totals[period][2] += impressions * float(row.get('position', 0))

    def metric(period):
        impressions, clicks, weighted = period
        return f'{impressions} / {clicks} / {weighted / impressions:.1f}' if impressions else '미관측'

    lines += ['| 가이드 | 검색어 | 직전 노출 / 클릭 / 평균 순위 | 최근 노출 / 클릭 / 평균 순위 |',
              '|---|---|---:|---:|']
    for label, slug in LONG_TAIL_GUIDES:
        page = f'https://linkwiki.info/blog/{slug}/'
        queries = by_page.get(page, {})
        top = sorted(queries, key=lambda q: (-queries[q][1][0], -queries[q][0][0], q))[:5]
        if not top:
            lines.append(f'| [{label}]({page}) | 미관측 | — | — |')
        for query in top:
            escaped = query.replace('|', '\\|').replace('\n', ' ')
            before, after = queries[query]
            lines.append(f'| [{label}]({page}) | {escaped} | {metric(before)} | {metric(after)} |')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--property', default=os.environ.get('GSC_PROPERTY', 'sc-domain:linkwiki.info'))
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--days', type=int, default=28)
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error('--days must be 1..90')
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=args.days - 1)
    token = access_token()
    keywords = query_performance(token, args.property, start.isoformat(), end.isoformat(), ['query'])
    pages = query_performance(token, args.property, start.isoformat(), end.isoformat(), ['page'])
    dates = query_performance(token, args.property, start.isoformat(), end.isoformat(), ['date'])
    query_pages = query_performance(token, args.property, start.isoformat(), end.isoformat(), ['query', 'page'], limit=1000)
    focused_keywords = None
    focused_pages = None
    focused_error = ''
    try:
        focused_keywords = query_performance(
            token, args.property, start.isoformat(), end.isoformat(),
            ['query'], limit=100, filter_groups=CORE_QUERY_FILTERS)
        focused_pages = query_performance(
            token, args.property, start.isoformat(), end.isoformat(),
            ['query', 'page'], limit=1000, filter_groups=CORE_QUERY_FILTERS)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        focused_error = type(exc).__name__
        if isinstance(exc, HTTPError):
            focused_error += f' HTTP {exc.code}'
    family_keyword_rows, family_error = [], ''
    try:
        family_keyword_rows = query_performance(
            token, args.property, start.isoformat(), end.isoformat(),
            ['query'], limit=1000, filter_groups=FAMILY_QUERY_FILTERS)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        family_error = type(exc).__name__
        if isinstance(exc, HTTPError):
            family_error += f' HTTP {exc.code}'
    # Use one dedicated filtered query×date request for exact disjoint
    # week comparisons, without mixing homepage/brand impressions.
    weekly_core_rows, weekly_core_error = [], ''
    try:
        weekly_core_rows = query_performance(
            token, args.property,
            (end - timedelta(days=13)).isoformat(), end.isoformat(),
            ['query', 'date'], limit=1000, filter_groups=CORE_QUERY_FILTERS)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        weekly_core_error = type(exc).__name__
        if isinstance(exc, HTTPError):
            weekly_core_error += f' HTTP {exc.code}'
    # A dedicated Korea-only comparison avoids conflating global positions
    # with Google Search traffic from South Korea.
    korea_core_rows, korea_core_error = [], ''
    try:
        korea_core_rows = query_performance(
            token, args.property,
            (end - timedelta(days=13)).isoformat(), end.isoformat(),
            ['query', 'date'], limit=1000,
            filter_groups=KOREA_CORE_QUERY_FILTERS)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        korea_core_error = type(exc).__name__
        if isinstance(exc, HTTPError):
            korea_core_error += f' HTTP {exc.code}'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inspections, inspection_error = collect_index_inspections(
        token, args.property, inspection_targets(pages, core_query_pages=focused_pages, as_of=date.today()))
    report = format_report(
        keywords, pages, start, end, args.property, dates, query_pages,
        focused_keyword_rows=focused_keywords,
        focused_query_page_rows=focused_pages, focused_error=focused_error)
    report += format_core_family_keyword_report(family_keyword_rows, family_error)
    report += format_core_keyword_weekly_comparison(
        weekly_core_rows, end.isoformat(), weekly_core_error)
    report += '\n\n## 한국 검색 이용자 기준 핵심 키워드 추이\n'
    report += ('\n- Google Search Console 국가 필터: 대한민국(kor). '
               '한국어 검색 전체 또는 구글 한국 도메인 순위와 동일하지 않습니다.\n'
               '- 아래 평균 순위는 실제 한국 이용자 대상 검색 노출의 가중 평균입니다.\n')
    report += format_core_keyword_weekly_comparison(
        korea_core_rows, end.isoformat(), korea_core_error, scope='korea')
    guide_rows, guide_error = [], ''
    try:
        guide_rows = query_performance(
            token, args.property, (end - timedelta(days=13)).isoformat(), end.isoformat(),
            ['query', 'page', 'date'], limit=1000, filter_groups=korea_guide_query_filters())
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        guide_error = type(exc).__name__
        if isinstance(exc, HTTPError):
            guide_error += f' HTTP {exc.code}'
    report += format_korea_guide_queries(guide_rows, end, guide_error)
    report += format_core_landing_page_split(focused_pages, focused_error)
    report += format_core_keyword_index_alignment(focused_pages, inspections, focused_error or inspection_error)
    report += format_index_inspection(inspections, inspection_error)
    report += format_search_visibility_inspection_conflicts(
        pages, inspections, end.isoformat(), inspection_error)
    sitemap_rows, sitemap_error = [], ''
    try:
        sitemap_rows = list_submitted_sitemaps(token, args.property)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        sitemap_error = type(exc).__name__
        if isinstance(exc, HTTPError):
            sitemap_error += f' HTTP {exc.code}'
    report += format_sitemap_health(sitemap_rows, sitemap_error)
    # Record machine-readable Google evidence alongside the human report.
    # The public URL Inspection API describes Google's stored copy, NOT live
    # indexability or evidence that a new deployment has been crawled.
    changes_path = ROOT / 'seo/significant-page-updates.json'
    changes = json.loads(changes_path.read_text(encoding='utf-8')) if changes_path.exists() else {}
    snapshot = {
        "schema": 1,
        "property": args.property,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "core_keywords": core_keyword_rows(
            focused_keywords if focused_keywords is not None else keywords,
            focused_pages if focused_pages is not None else query_pages),
        "global_core_weekly": core_keyword_weekly_comparison(
            weekly_core_rows, end.isoformat()) if not weekly_core_error else [],
        "global_core_weekly_error": weekly_core_error,
        "korea_core_weekly": core_keyword_weekly_comparison(
            korea_core_rows, end.isoformat()) if not korea_core_error else [],
        "korea_core_weekly_error": korea_core_error,
        "core_query_error": focused_error,
        "inspections": inspections,
        "inspection_error": inspection_error,
        "significant_page_updates": changes,
        "sitemaps": sitemap_rows,
        "sitemap_error": sitemap_error,
    }
    args.output.with_name('search-console-snapshot.json').write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.output.write_text(report, encoding='utf-8')
    print(f'Wrote {args.output}: {len(keywords)} queries, {len(pages)} pages')


if __name__ == '__main__':
    main()
