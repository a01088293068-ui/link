import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'seo' / 'search_console_monitor.py'
spec = importlib.util.spec_from_file_location('gsc_monitor', SOURCE)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class SearchConsoleMonitorTests(unittest.TestCase):
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
        report = monitor.format_report([], [], '2026-09-01', '2026-09-28',
                                       'sc-domain:linkwiki.info', days)
        self.assertIn('최근 7일: 노출 77회 · 클릭 7회', report)
        self.assertIn('직전 7일: 노출 28회 · 클릭 7회', report)
        short = monitor.format_report([], [], '2026-09-01', '2026-09-28',
                                      'sc-domain:linkwiki.info', days[:13])
        self.assertNotIn('최근 7일과 직전 7일 비교', short)

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
