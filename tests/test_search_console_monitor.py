import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'seo' / 'search_console_monitor.py'
spec = importlib.util.spec_from_file_location('gsc_monitor', SOURCE)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class SearchConsoleMonitorTests(unittest.TestCase):
    def test_latest_published_posts_are_inspected_without_google_impressions(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            posts = root / 'content'
            posts.mkdir()
            for day in ('20261027', '20261028', '20261030', '20261102'):
                (posts / f'seo-{day}-example.md').write_text('# SEO title', encoding='utf-8')
            with patch.object(monitor, 'ROOT', root):
                recent = monitor.recent_published_post_urls()
                targets = monitor.inspection_targets([], limit=20)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0], 'https://linkwiki.info/blog/seo-20261102-example/')
        self.assertNotIn('https://linkwiki.info/blog/seo-20261027-example/', recent)
        self.assertTrue(all(url in targets for url in recent))
        self.assertLessEqual(len(targets), 20)

    def test_inspection_prioritizes_all_eight_categories_and_respects_limit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'content').mkdir()
            (root / 'content/seo-20261102-example.md').write_text('# SEO', encoding='utf-8')
            with patch.object(monitor, 'ROOT', root):
                limited = monitor.inspection_targets([], limit=5)
                targets = monitor.inspection_targets([], limit=20)
        self.assertEqual(limited, list(monitor.INSPECT_URLS[:5]))
        self.assertIn('https://linkwiki.info/', targets)
        self.assertIn('https://linkwiki.info/directory', targets)
        self.assertIn('https://linkwiki.info/categories/', targets)
        for slug in ('community', 'korean', 'comics-directory', 'webtoon',
                     'ai', 'search', 'sports', 'video'):
            self.assertIn('https://linkwiki.info/categories/' + slug, targets)
        self.assertIn('https://linkwiki.info/blog/seo-20261102-example/', targets)
        self.assertEqual(len(targets), len(set(targets)))

    def test_english_and_korean_exclusion_states_are_counted(self):
        rows = [
            {"url": "https://linkwiki.info/", "verdict": "PASS",
             "coverage": "Submitted and indexed"},
            {"url": "https://linkwiki.info/directory", "verdict": "NEUTRAL",
             "coverage": "Crawled - currently not indexed"},
            {"url": "https://linkwiki.info/categories/ai", "verdict": "NEUTRAL",
             "coverage": "URL is unknown to Google"},
            {"url": "https://linkwiki.info/categories/sports", "verdict": "NEUTRAL",
             "coverage": "크롤링됨 - 현재 색인이 생성되지 않음"},
            {"url": "https://linkwiki.info/categories/video", "verdict": "NEUTRAL",
             "coverage": "Google에 아직 알려지지 않은 URL입니다."},
        ]
        report = monitor.format_index_inspection(rows)
        self.assertIn("검사한 URL: 5개 · 색인 PASS: 1개", report)
        self.assertIn("Google에 알려지지 않음: 2개", report)
        self.assertIn("크롤링 후 미색인: 2개", report)

    def test_inspection_continues_after_single_url_not_found(self):
        from urllib.error import HTTPError
        calls = []
        def inspector(token, property_url, url):
            calls.append(url)
            if url.endswith('/missing'):
                raise HTTPError(url, 404, 'not found', {}, None)
            return {'url': url, 'verdict': 'PASS'}
        urls = ['https://linkwiki.info/missing', 'https://linkwiki.info/']
        rows, error = monitor.collect_index_inspections('token', 'property', urls, inspector)
        self.assertEqual(calls, urls)
        self.assertEqual(rows, [{'url': urls[1], 'verdict': 'PASS'}])
        self.assertIn('HTTP 404', error)
        self.assertIn(urls[0], error)

    def test_inspection_stops_after_auth_or_quota_error(self):
        from urllib.error import HTTPError
        for code in (401, 403, 429, 503):
            with self.subTest(code=code):
                calls = []
                def inspector(token, property_url, url):
                    calls.append(url)
                    raise HTTPError(url, code, 'unavailable', {}, None)
                rows, error = monitor.collect_index_inspections(
                    'token', 'property', ['https://linkwiki.info/a', 'https://linkwiki.info/b'], inspector)
                self.assertEqual(rows, [])
                self.assertEqual(len(calls), 1)
                self.assertIn(f'HTTP {code}', error)
                self.assertNotIn('색인되지 않음', error)

    def test_core_three_keyword_rows_aggregate_space_variants_and_weight_positions(self):
        rows = [
            {'keys': ['주소모음'], 'impressions': 3, 'clicks': 1, 'position': 20},
            {'keys': ['주소 모음'], 'impressions': 1, 'clicks': 0, 'position': 40},
            {'keys': ['링크 모음'], 'impressions': 2, 'clicks': 1, 'position': 12},
            {'keys': ['링크위키'], 'impressions': 50, 'clicks': 20, 'position': 1},
        ]
        query_pages = [
            {'keys': ['주소모음', 'https://linkwiki.info/'], 'impressions': 3},
            {'keys': ['주소 모음', 'https://linkwiki.info/directory'], 'impressions': 1},
        ]
        actual = monitor.core_keyword_rows(rows, query_pages)
        self.assertEqual([r['keyword'] for r in actual], ['주소모음', '링크모음', '사이트모음'])
        self.assertEqual((actual[0]['impressions'], actual[0]['clicks'], actual[0]['position']), (4, 1, 25.0))
        self.assertEqual(actual[0]['pages'],
                         ['https://linkwiki.info/', 'https://linkwiki.info/directory'])
        self.assertEqual(actual[1]['impressions'], 2)
        self.assertFalse(actual[2]['observed'])
        self.assertIsNone(actual[2]['position'])

    def test_core_keyword_section_never_invents_unobserved_rankings(self):
        report = monitor.format_report([], [], '2026-10-01', '2026-10-28', 'sc-domain:linkwiki.info')
        self.assertIn('## 핵심 목표 키워드 3종 실적', report)
        for term in ('주소모음', '링크모음', '사이트모음'):
            self.assertIn(f'| {term} | 데이터 없음 | - | - | - |', report)

    def test_core_filter_is_real_search_console_query_regex(self):
        import json
        rows = []
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def read(self):
                return b'{"rows":[]}'
        with patch.object(monitor, 'urlopen', return_value=Response()) as mocked:
            rows = monitor.query_performance(
                "token", "sc-domain:linkwiki.info", "2026-10-01", "2026-10-28",
                ["query"], filter_groups=monitor.CORE_QUERY_FILTERS)
        self.assertEqual(rows, [])
        payload = json.loads(mocked.call_args.args[0].data)
        flt = payload["dimensionFilterGroups"][0]["filters"][0]
        self.assertEqual(flt["dimension"], "query")
        self.assertEqual(flt["operator"], "includingRegex")
        self.assertIn("주소", flt["expression"])
        self.assertIn("링크", flt["expression"])
        self.assertIn("사이트", flt["expression"])
        self.assertEqual(payload["dimensions"], ["query"])

    def test_focused_keyword_rows_not_obscured_by_top_query_listing(self):
        focused = [
            {"keys": ["주소 모음"], "impressions": 2, "clicks": 1, "position": 64}
        ]
        report = monitor.format_report(
            [{"keys": ["링크위키"], "impressions": 40, "clicks": 20, "position": 1}],
            [], "2026-10-01", "2026-10-28", "sc-domain:linkwiki.info",
            focused_keyword_rows=focused,
            focused_query_page_rows=[{
                "keys": ["주소 모음", "https://linkwiki.info/directory"],
                "impressions": 2, "clicks": 1, "position": 64,
            }])
        self.assertIn("| 주소모음 | 2 | 1 | 64.0 | https://linkwiki.info/directory |", report)
        self.assertIn("| 링크모음 | 데이터 없음 | - | - | - |", report)
        self.assertNotIn("| 링크모음 | 40 | 20", report)

    def test_api_request_and_response(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def read(self):
                return b'{"rows":[{"keys":["linkwiki"],"clicks":2}]}'
        with patch.object(monitor, 'urlopen', return_value=Response()) as mocked:
            rows = monitor.query_performance('token', 'sc-domain:linkwiki.info',
                                             '2026-09-01', '2026-09-28', ['query'])
        request = mocked.call_args.args[0]
        self.assertIn('sc-domain%3Alinkwiki.info', request.full_url)
        self.assertEqual(request.get_header('Authorization'), 'Bearer token')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(rows[0]['clicks'], 2)

    def test_index_inspection_reads_indexed_version_without_submission(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def read(self):
                return (b'{"inspectionResult":{"indexStatusResult":'
                        b'{"verdict":"PASS","coverageState":"Submitted and indexed",'
                        b'"googleCanonical":"https://linkwiki.info/"}}}')
        with patch.object(monitor, 'urlopen', return_value=Response()) as mocked:
            row = monitor.inspect_index('token', 'sc-domain:linkwiki.info',
                                        'https://linkwiki.info/')
        self.assertEqual(row['verdict'], 'PASS')
        self.assertEqual(row['google_canonical'], 'https://linkwiki.info/')
        request = mocked.call_args.args[0]
        self.assertEqual(request.method, 'POST')
        self.assertIn('/urlInspection/index:inspect', request.full_url)
        self.assertEqual(request.get_header('Authorization'), 'Bearer token')

    def test_inspection_targets_include_real_google_url_and_html_canonical(self):
        rows = [
            {'keys': ['https://linkwiki.info/guides/choose-directory'], 'impressions': 8},
            {'keys': ['https://other.example/private'], 'impressions': 50},
            {'keys': ['https://linkwiki.info/categories/sports'], 'impressions': 5},
        ]
        targets = monitor.inspection_targets(rows)
        self.assertIn('https://linkwiki.info/guides/choose-directory', targets)
        self.assertNotIn('https://linkwiki.info/guides/choose-directory.html', targets)
        self.assertIn('https://linkwiki.info/categories/sports', targets)
        self.assertNotIn('https://linkwiki.info/categories/sports.html', targets)
        self.assertNotIn('https://other.example/private', targets)
        self.assertIn('https://linkwiki.info/directory', targets)
        self.assertLessEqual(len(targets), 15)

    def test_inspection_legacy_html_observation_checks_both_urls(self):
        rows = [
            {'keys': ['https://linkwiki.info/categories/ai.html'], 'impressions': 9},
            {'keys': ['https://linkwiki.info/guides/security.html'], 'impressions': 4},
            {'keys': ['https://linkwiki.info/index.html'], 'impressions': 1},
        ]
        targets = monitor.inspection_targets(rows)
        self.assertIn('https://linkwiki.info/categories/ai', targets)
        self.assertIn('https://linkwiki.info/categories/ai.html', targets)
        self.assertIn('https://linkwiki.info/guides/security', targets)
        self.assertIn('https://linkwiki.info/guides/security.html', targets)
        self.assertIn('https://linkwiki.info/', targets)
        self.assertLessEqual(len(targets), 15)

    def test_index_report_prioritizes_unknown_and_crawled_not_indexed_urls(self):
        inspected = [
            {"url": "https://linkwiki.info/", "verdict": "PASS",
             "coverage": "Submitted and indexed"},
            {"url": "https://linkwiki.info/directory", "verdict": "NEUTRAL",
             "coverage": "Google에는 아직 알려지지 않은 URL입니다."},
            {"url": "https://linkwiki.info/categories/ai", "verdict": "NEUTRAL",
             "coverage": "크롤링됨 - 현재 색인이 생성되지 않음"},
        ]
        output = monitor.format_index_inspection(inspected)
        self.assertIn("검사한 URL: 3개 · 색인 PASS: 1개", output)
        self.assertIn("Google에 알려지지 않음: 1개", output)
        self.assertIn("크롤링 후 미색인: 1개", output)
        self.assertLess(output.index("https://linkwiki.info/directory —"),
                        output.index("https://linkwiki.info/categories/ai —"))
        self.assertIn("사이트 전체의 색인 수가 아닙니다", output)

    def test_inspection_error_is_not_reported_as_not_indexed(self):
        report = monitor.format_index_inspection([], 'HTTPError (inspect API unavailable or restricted)')
        self.assertIn('색인 조회 일부 또는 전체 실패', report)
        self.assertNotIn('색인되지 않음', report)

    def test_empty_report(self):
        result = monitor.format_report([], [], '2026-09-01', '2026-09-28', 'sc-domain:linkwiki.info')
        self.assertIn('데이터 없음', result)

    def test_report_values(self):
        rows = [{'keys': ['주소모음'], 'impressions': 100, 'clicks': 3, 'ctr': .03, 'position': 9.8}]
        result = monitor.format_report(rows, [], '2026-09-01', '2026-09-28', 'sc-domain:linkwiki.info')
        self.assertIn('주소모음 | 100 | 3 | 3.0% | 9.8', result)


    def test_no_query_rows_with_page_rows_is_not_zero_impressions(self):
        pages = [{'keys': ['https://linkwiki.info/'], 'impressions': 4, 'clicks': 0, 'position': 31}]
        report = monitor.format_report([], pages, '2026-09-01', '2026-09-28', 'sc-domain:linkwiki.info')
        self.assertIn('검색어 행은 0개지만 페이지별 데이터가 있습니다', report)
        self.assertIn('노출 0회로 해석하지 마세요', report)

    def test_page_opportunity_queue_works_without_search_queries(self):
        pages = [
            {'keys': ['https://linkwiki.info/directory'], 'impressions': 16, 'clicks': 1, 'position': 18},
            {'keys': ['https://linkwiki.info/categories/ai'], 'impressions': 5, 'clicks': 0, 'position': 42},
            {'keys': ['https://linkwiki.info/'], 'impressions': 50, 'clicks': 0, 'position': 61},
        ]
        report = monitor.format_report([], pages, '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info')
        section = report.split('## 노출 페이지 우선 개선 후보')[1].split('## 최근 날짜별 추세')[0]
        self.assertIn('https://linkwiki.info/directory | 16 | 1 | 18.0', section)
        self.assertIn('https://linkwiki.info/categories/ai | 5 | 0 | 42.0', section)
        self.assertNotIn('https://linkwiki.info/ | 50', section)

    def test_opportunity_queue_uses_observed_impressions_and_positions(self):
        rows = [
            {'keys': ['커뮤니티 사이트모음'], 'impressions': 18, 'clicks': 1, 'position': 12},
            {'keys': ['웹툰 링크모음'], 'impressions': 7, 'clicks': 0, 'position': 24},
            {'keys': ['주소모음'], 'impressions': 100, 'clicks': 2, 'position': 55},
            {'keys': ['희소 검색어'], 'impressions': 1, 'clicks': 0, 'position': 15},
        ]
        report = monitor.format_report(rows, [], '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info')
        queue = report.split('## 먼저 개선할 연관 검색어 후보')[1].split('## 페이지 상위')[0]
        self.assertIn('커뮤니티 사이트모음 | 18 | 1 | 12.0', queue)
        self.assertIn('웹툰 링크모음 | 7 | 0 | 24.0', queue)
        self.assertNotIn('주소모음 |', queue)
        self.assertNotIn('희소 검색어 |', queue)

    def test_query_page_pairs_identify_actual_landing_pages(self):
        pairs = [
            {'keys': ['주소모음 사이트 추천', 'https://linkwiki.info/guides/directory-comparison'],
             'impressions': 14, 'clicks': 1, 'position': 13.2},
            {'keys': ['링크모음', 'https://linkwiki.info/'],
             'impressions': 30, 'clicks': 0, 'position': 45},
            {'keys': ['검색량 적은 키워드', 'https://linkwiki.info/directory'],
             'impressions': 1, 'clicks': 0, 'position': 17},
        ]
        report = monitor.format_report([], [], '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info', query_page_rows=pairs)
        section = report.split('## 검색어별 실제 노출 페이지')[1].split('## 페이지 상위')[0]
        self.assertIn('주소모음 사이트 추천 | https://linkwiki.info/guides/directory-comparison | 14 | 1 | 13.2', section)
        self.assertNotIn('링크모음 |', section)
        self.assertNotIn('검색량 적은 키워드 |', section)

    def test_empty_opportunity_queue_has_explicit_note(self):
        report = monitor.format_report([], [], '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info')
        self.assertIn('조건에 맞는 검색어 없음', report)

    def test_weekly_comparison_requires_fourteen_dates(self):
        days = [{'keys': [f'2026-09-{day:02}'], 'impressions': day, 'clicks': 1, 'position': 20}
                for day in range(1, 15)]
        report = monitor.format_report([], [], '2026-09-01', '2026-09-14',
                                       'sc-domain:linkwiki.info', days)
        self.assertIn('최근 7일: 노출 77회 · 클릭 7회', report)
        self.assertIn('직전 7일: 노출 28회 · 클릭 7회', report)
        short = monitor.format_report([], [], '2026-09-02', '2026-09-14',
                                      'sc-domain:linkwiki.info', days[:13])
        self.assertNotIn('최근 7일과 직전 7일 비교', short)

    def test_weekly_comparison_uses_calendar_days_when_missing_dates(self):
        dates = [
            {'keys': ['2026-09-01'], 'impressions': 90, 'clicks': 9, 'position': 2},
            {'keys': ['2026-09-16'], 'impressions': 4, 'clicks': 1, 'position': 6},
            {'keys': ['2026-09-28'], 'impressions': 3, 'clicks': 0, 'position': 8},
        ]
        report = monitor.format_report([], [], '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info', dates)
        self.assertIn('최근 7일: 노출 3회 · 클릭 0회', report)
        self.assertIn('직전 7일: 노출 4회 · 클릭 1회', report)
        self.assertNotIn('최근 7일: 노출 97회', report)

    def test_date_aggregates_when_queries_hidden(self):
        days = [
            {'keys': ['2026-09-27'], 'impressions': 12, 'clicks': 1, 'position': 23.2},
            {'keys': ['2026-09-28'], 'impressions': 8, 'clicks': 0, 'position': 17.4},
        ]
        result = monitor.format_report([], [], '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info', days)
        self.assertIn('노출: 20회 · 클릭: 1회 · CTR: 5.0%', result)
        self.assertIn('| 2026-09-28 | 8 | 0 | 17.4 |', result)
        self.assertLess(result.index('## 검색어 상위'), result.index('## 최근 날짜별 추세'))


if __name__ == '__main__':
    unittest.main()
