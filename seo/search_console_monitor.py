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
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

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


def query_performance(token, property_url, start_date, end_date, dimensions, limit=100):
    endpoint = ('https://www.googleapis.com/webmasters/v3/sites/' +
                quote(property_url, safe='') + '/searchAnalytics/query')
    payload = {'startDate': start_date, 'endDate': end_date, 'dimensions': dimensions,
               'rowLimit': limit, 'type': 'web'}
    request = Request(endpoint, json.dumps(payload).encode('utf-8'),
                      {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                      method='POST')
    with urlopen(request, timeout=30) as response:
        return json.load(response).get('rows', [])


def format_report(keyword_rows, page_rows, start_date, end_date, property_url, date_rows=None):
    lines = ['# 링크위키 Search Console 실적', '',
             f'- 속성: `{property_url}`', f'- 조회 기간: {start_date} ~ {end_date}',
             '- 데이터: Google Search Console API. 검색량이나 실시간 순위가 아닙니다.', '',
             '## 검색어 상위 30개', '', '| 검색어 | 노출 | 클릭 | CTR | 평균 순위 |',
             '|---|---:|---:|---:|---:|']
    # Date-based totals include impressions from anonymized query rows.
    daily = sorted(date_rows or [], key=lambda row: (row.get('keys') or [''])[0])
    if daily:
        clicks = sum(int(row.get('clicks', 0)) for row in daily)
        impressions = sum(int(row.get('impressions', 0)) for row in daily)
        ctr = clicks / impressions * 100 if impressions else 0
        lines[6:6] = [
            '## 전체 검색 성과 (날짜별 합계)', '',
            f'- 노출: {impressions:,}회 · 클릭: {clicks:,}회 · CTR: {ctr:.1f}%',
            '- 검색어 표와 전체 합계는 익명 검색어 처리로 차이가 날 수 있습니다.', '',
        ]
    else:
        lines[6:6] = ['## 전체 검색 성과', '', '날짜별 검색 성과 데이터 없음', '']
    if not keyword_rows and page_rows:
        lines.extend(['', '검색어 행은 0개지만 페이지별 데이터가 있습니다. 검색어 익명 처리나 집계 기준 차이일 수 있으므로 노출 0회로 해석하지 마세요.', ''])
    if len(daily) >= 14:
        recent = daily[-7:]
        previous = daily[-14:-7]
        recent_impressions = sum(int(row.get('impressions', 0)) for row in recent)
        previous_impressions = sum(int(row.get('impressions', 0)) for row in previous)
        recent_clicks = sum(int(row.get('clicks', 0)) for row in recent)
        previous_clicks = sum(int(row.get('clicks', 0)) for row in previous)
        lines.extend(['', '## 최근 7일과 직전 7일 비교', '',
                      f'- 최근 7일: 노출 {recent_impressions:,}회 · 클릭 {recent_clicks:,}회',
                      f'- 직전 7일: 노출 {previous_impressions:,}회 · 클릭 {previous_clicks:,}회',
                      '- 집계된 날짜가 14일 이상일 때만 비교하며, 데이터가 적으면 일별 변동이 큽니다.', ''])
    for row in keyword_rows[:30]:
        key = str((row.get('keys') or [''])[0]).replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {key} | {int(row.get('impressions', 0))} | {int(row.get('clicks', 0))} | "
                     f"{row.get('ctr', 0)*100:.1f}% | {row.get('position', 0):.1f} |")
    if not keyword_rows:
        lines.append('| 데이터 없음 | - | - | - | - |')
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
    lines.extend(['', '## 페이지 상위 30개', '', '| URL | 노출 | 클릭 | 평균 순위 |',
                  '|---|---:|---:|---:|'])
    for row in page_rows[:30]:
        key = str((row.get('keys') or [''])[0]).replace('|', '%7C')
        lines.append(f"| {key} | {int(row.get('impressions', 0))} | "
                     f"{int(row.get('clicks', 0))} | {row.get('position', 0):.1f} |")
    if not page_rows:
        lines.append('| 데이터 없음 | - | - | - |')
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(format_report(keywords, pages, start, end, args.property, dates), encoding='utf-8')
    print(f'Wrote {args.output}: {len(keywords)} queries, {len(pages)} pages')


if __name__ == '__main__':
    main()
