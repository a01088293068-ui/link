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
    with urlopen(request, timeout=30) as response:
        return json.load(response).get('rows', [])


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

def inspection_targets(page_rows, limit=20):
    """Prioritize deployed extensionless canonicals and inspect observed variants.

    Cloudflare serves .html files at extensionless canonical URLs. When Search
    Console actually reports a .html URL, inspect both that observed address
    and its canonical so a legacy redirect does not mask the indexed page.
    """
    from urllib.parse import urlsplit
    urls = list(INSPECT_URLS[:limit])
    seen = set(urls)
    for url in recent_published_post_urls():
        if url not in seen and len(urls) < limit:
            urls.append(url)
            seen.add(url)
    for row in sorted(page_rows, key=lambda r: -int(r.get('impressions', 0))):
        observed = str((row.get('keys') or [''])[0]).strip()
        parts = urlsplit(observed)
        if parts.scheme != 'https' or parts.netloc != 'linkwiki.info':
            continue
        if parts.query or parts.fragment:
            continue
        path = parts.path.rstrip('/')
        candidates = [observed]
        if path == '/index.html':
            candidates.insert(0, 'https://linkwiki.info/')
        elif path.endswith('.html'):
            candidates.insert(0, 'https://linkwiki.info' + path[:-5])
        for url in candidates:
            if url not in seen and len(urls) < limit:
                urls.append(url)
                seen.add(url)
    return urls


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
        if (not technical_index_obstacles(row)
                and row.get('verdict') not in ('PASS', None, 'UNKNOWN')):
            lines.append('- ' + url + ': 명시적인 기술 차단 신호가 확인되지 않았습니다. '
                         '이 결과만으로 콘텐츠 품질이 미색인 원인이라고 단정할 수 없습니다.')
    lines.extend(['', '- Google URL Inspection API의 색인 저장본 기준으로, '
                  '현재 실시간 HTTP 상태와 다를 수 있습니다.',
                  '- sitemap 및 발견 경로는 Google API에서 일부만 제공할 수 있습니다.', ''])
    return '\n'.join(lines)


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
                         str(row.get('coverage', '정보 없음')).replace('\\n', ' '))
    lines.append(priority_index_checks(rows))
    lines.append(technical_index_diagnostic(rows))
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
        key = str((row.get('keys') or [''])[0]).replace('|', '\\|').replace('\\n', ' ')
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
        query = str(keys[0]).replace('|', '\\|').replace('\\n', ' ')
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inspections, inspection_error = collect_index_inspections(
        token, args.property, inspection_targets(pages))
    report = format_report(
        keywords, pages, start, end, args.property, dates, query_pages,
        focused_keyword_rows=focused_keywords,
        focused_query_page_rows=focused_pages, focused_error=focused_error)
    report += format_index_inspection(inspections, inspection_error)
    args.output.write_text(report, encoding='utf-8')
    print(f'Wrote {args.output}: {len(keywords)} queries, {len(pages)} pages')


if __name__ == '__main__':
    main()
