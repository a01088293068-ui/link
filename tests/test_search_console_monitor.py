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
    def test_scheduled_gsc_reports_are_not_cancelled_by_deployment_bursts(self):
        workflow = (SOURCE.parents[1] /
                    ".github/workflows/search-console-monitor.yml").read_text(encoding="utf-8")
        self.assertIn("group: linkwiki-gsc-measurement", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("cron: '25 3 * * *'", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn("'seo/search_console_monitor.py'", workflow)
        self.assertIn("'tests/test_search_console_monitor.py'", workflow)
        self.assertIn("name: search-console-performance", workflow)

    def test_gsc_failure_keeps_diagnostic_artifact_without_secrets(self):
        workflow = (SOURCE.parents[1] /
                    ".github/workflows/search-console-monitor.yml").read_text(encoding="utf-8")
        self.assertIn("id: gsc_fetch", workflow)
        self.assertIn("status: missing_google_service_account_secret", workflow)
        self.assertIn("status: google_api_or_report_error", workflow)
        self.assertIn("status: completed", workflow)
        self.assertIn("if: always() && steps.gsc_fetch.outcome != 'skipped'", workflow)
        self.assertIn("seo/search-console-run-status.txt", workflow)
        self.assertIn("seo/search-console-report.md", workflow)
        self.assertIn("retention-days: 30", workflow)

    def test_google_discovery_report_does_not_confuse_missing_hints_with_no_discovery(self):
        directory = "https://linkwiki.info/directory"
        rows = [{
            "url": directory,
            "verdict": "NEUTRAL",
            "coverage": "Crawled - currently not indexed",
            "sitemaps": ["https://linkwiki.info/sitemap.xml"],
            "referring_urls": ["https://linkwiki.info/", "https://example.org/review"],
        }, {
            "url": "https://linkwiki.info/",
            "verdict": "PASS",
            "sitemaps": [],
            "referring_urls": [],
        }]
        output = monitor.format_google_discovery_evidence(rows)
        self.assertIn("https://linkwiki.info/sitemap.xml", output)
        self.assertIn("https://example.org/review", output)
        self.assertIn("정보 미제공", output)
        self.assertIn("URL 검사 미수행", output)
        self.assertNotIn("발견 경로 없음", output)
        combined = monitor.format_index_inspection(rows)
        self.assertIn("Google이 보고한 핵심 URL 발견 경로", combined)
        failed = monitor.format_google_discovery_evidence(
            rows, error="https://linkwiki.info/categories/: HTTPError (HTTP 429)")
        self.assertIn("조회 실패·일부 미완료", failed)
        self.assertNotIn("URL 검사 미수행", failed)
        failed_report = monitor.format_index_inspection(
            rows, error="HTTPError (HTTP 429)")
        self.assertIn("조회 실패·일부 미완료", failed_report)
        self.assertIn("색인 조회 일부 또는 전체 실패", failed_report)

    def test_core_keyword_weekly_comparison_is_date_scoped_and_weighted(self):
        rows = [
            {'keys': ['주소모음', '2026-10-26'], 'impressions': 2, 'clicks': 1, 'position': 100},
            {'keys': ['주소 모음', '2026-10-30'], 'impressions': 1, 'clicks': 0, 'position': 90},
            {'keys': ['주소모음', '2026-11-01'], 'impressions': 3, 'clicks': 1, 'position': 30},
            {'keys': ['링크모음', '2026-10-29'], 'impressions': 1, 'clicks': 0, 'position': 120},
            {'keys': ['링크모음', '2026-11-05'], 'impressions': 2, 'clicks': 1, 'position': 40},
            {'keys': ['주소모음', '2026-10-22'], 'impressions': 100, 'clicks': 50, 'position': 1},
            {'keys': ['링크위키', '2026-11-05'], 'impressions': 300, 'clicks': 20, 'position': 1},
        ]
        comparison = monitor.core_keyword_weekly_comparison(rows, '2026-11-05')
        address = comparison[0]
        self.assertEqual(address['previous']['impressions'], 2)
        self.assertEqual(address['recent']['impressions'], 4)
        self.assertEqual(address['recent']['clicks'], 1)
        self.assertEqual(address['recent']['position'], 45.0)
        self.assertEqual(comparison[1]['recent']['position'], 40.0)
        self.assertFalse(comparison[2]['recent']['observed'])
        report = monitor.format_core_keyword_weekly_comparison(rows, '2026-11-05')
        self.assertIn('주소모음 | 2회 · 1회 | 4회 · 1회 | +2회', report)
        self.assertIn('45.0위', report)
        self.assertIn('사이트모음 | 관측 없음 | 관측 없음 | 비교 불가', report)
        self.assertNotIn('300회', report)

    def test_korean_market_core_filter_and_distinct_report_title(self):
        groups = monitor.KOREA_CORE_QUERY_FILTERS
        self.assertEqual(len(groups), 1)
        filters = groups[0]['filters']
        self.assertEqual(filters[0]['dimension'], 'query')
        self.assertEqual(filters[1], {
            'dimension': 'country', 'operator': 'equals', 'expression': 'kor',
        })
        rows = [
            {'keys': ['주소모음', '2026-11-05'],
             'impressions': 5, 'clicks': 2, 'position': 21.0}
        ]
        korea = monitor.format_core_keyword_weekly_comparison(
            rows, '2026-11-05', scope='korea')
        global_report = monitor.format_core_keyword_weekly_comparison(
            rows, '2026-11-05')
        self.assertIn('대한민국 이용자 기준 최근 7일', korea)
        self.assertNotIn('대한민국 이용자 기준', global_report)
        self.assertIn('주소모음 | 관측 없음 | 5회 · 2회', korea)
        self.assertIn('21.0위', korea)

    def test_korean_market_api_errors_remain_explicit(self):
        report = monitor.format_core_keyword_weekly_comparison(
            [], '2026-11-05', 'HTTPError HTTP 403', scope='korea')
        self.assertIn('조회 실패', report)
        self.assertNotIn('| 주소모음 | 관측 없음', report)

    def test_core_keyword_weekly_query_failure_is_not_zero_impressions(self):
        report = monitor.format_core_keyword_weekly_comparison([], '2026-11-05',
                                                               'HTTPError HTTP 403')
        self.assertIn('조회 실패', report)
        self.assertNotIn('| 주소모음 | 관측 없음', report)

    def test_private_gsc_reporting_uses_controlled_schedule_and_manual_runs(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/search-console-monitor.yml').read_text(encoding='utf-8')
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("cron: '25 3 * * *'", workflow)
        self.assertIn("group: linkwiki-gsc-measurement", workflow)
        self.assertIn("vars.GSC_MONITOR_ENABLED == 'true'", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("name: search-console-performance", workflow)
        self.assertNotIn("contents: write", workflow)

    def test_google_string_zero_error_count_is_not_a_failure(self):
        report = monitor.format_sitemap_health([{
            'path': 'https://linkwiki.info/sitemap.xml',
            'isPending': True, 'errors': '0', 'warnings': '0',
            'lastSubmitted': '2026-10-27T06:35:03Z',
        }])
        self.assertIn('Google이 아직 사이트맵 처리를 완료하지 않았습니다', report)
        self.assertNotIn('사이트맵 처리 오류를 Search Console에서 확인하세요', report)
        self.assertIn('오류: 0 · 경고: 0', report)

    def test_gsc_sitemap_health_distinguishes_submission_and_download(self):
        absent = monitor.format_sitemap_health([])
        self.assertIn('제출 기록이 확인되지 않았습니다', absent)
        self.assertIn('robots.txt', absent)
        present = monitor.format_sitemap_health([{
            'path': 'https://linkwiki.info/sitemap.xml',
            'lastSubmitted': '2026-11-01T00:00:00Z',
            'lastDownloaded': '2026-11-08T01:00:00Z',
            'warnings': 0, 'errors': 0,
        }])
        self.assertIn('제출 기록: 확인', present)
        self.assertIn('2026-11-08T01:00:00Z', present)
        self.assertIn('색인은 보장되지 않습니다', present)
        bad = monitor.format_sitemap_health([{
            'path': 'https://linkwiki.info/sitemap.xml', 'errors': 2
        }])
        self.assertIn('사이트맵 처리 오류', bad)
        self.assertIn('조회 실패', monitor.format_sitemap_health([], 'HTTPError HTTP 403'))

    def test_report_does_not_confuse_failed_current_sitemap_with_working_v2(self):
        report = monitor.format_sitemap_health([
            {'path': 'https://linkwiki.info/sitemap.xml',
             'lastSubmitted': '2026-11-07T00:00:00Z',
             'lastDownloaded': '', 'errors': 1},
            {'path': 'https://linkwiki.info/sitemap-v2.xml',
             'lastSubmitted': '2026-10-24T00:00:00Z',
             'lastDownloaded': '2026-10-24T13:00:00Z',
             'errors': 0, 'warnings': 0},
        ])
        self.assertIn('사이트맵 처리 오류', report)
        self.assertIn('대체 사이트맵(sitemap-v2.xml)', report)
        self.assertIn('2026-10-24T13:00:00Z', report)
        self.assertIn('대체 사이트맵은 Google에 다운로드 기록이 있습니다', report)
        self.assertNotIn('모든 사이트맵 실패', report)

    def test_v2_not_submitted_does_not_invent_success(self):
        report = monitor.format_sitemap_health([{
            'path': 'https://linkwiki.info/sitemap.xml',
            'lastSubmitted': '2026-11-07T00:00:00Z',
        }])
        self.assertIn('대체 사이트맵 제출 기록이 없습니다', report)
        self.assertNotIn('대체 사이트맵은 Google에 다운로드 기록이 있습니다', report)

    def test_sitemap_health_api_is_read_only(self):
        from io import BytesIO
        from unittest.mock import patch
        class Response:
            def __enter__(self): return BytesIO(b'{"sitemap":[{"path":"https://linkwiki.info/sitemap.xml"}]}')
            def __exit__(self, *args): return False
        with patch.object(monitor, 'urlopen', return_value=Response()) as open_url:
            rows = monitor.list_submitted_sitemaps('fake-token', 'sc-domain:linkwiki.info')
        self.assertEqual(rows[0]['path'], 'https://linkwiki.info/sitemap.xml')
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertIn('sc-domain%3Alinkwiki.info', request.full_url)

    def test_crawl_edit_report_includes_all_eight_updated_category_urls(self):
        report = monitor.crawl_after_significant_change(
            [], {'/': '2026-11-07', '/directory': '2026-11-08',
                 '/categories/ai': '2026-11-08',
                 '/categories/video': '2026-11-08'})
        self.assertIn('https://linkwiki.info/categories/ai', report)
        self.assertIn('https://linkwiki.info/categories/video', report)
        self.assertIn('조회 결과 없음 · 재크롤링 여부 불명', report)

    def test_google_crawl_dates_are_compared_with_real_content_edit_dates(self):
        from seo.search_console_monitor import crawl_after_significant_change
        report = crawl_after_significant_change([
            {'url': 'https://linkwiki.info/directory',
             'last_crawl': '2026-11-03T13:00:00Z'},
            {'url': 'https://linkwiki.info/', 'last_crawl': '2026-11-07T14:00:00Z'},
            {'url': 'https://linkwiki.info/categories/',
             'last_crawl': '2026-11-08T01:00:00Z'},
        ], {'/': '2026-11-07', '/directory': '2026-11-07',
            '/categories/': '2026-11-07'})
        self.assertIn('최신 수정 이전 크롤링 · 변경 후 재크롤링 미확인', report)
        self.assertIn('같은 날짜 크롤링 · 수정 전후 순서 미확정', report)
        self.assertIn('콘텐츠 변경 날짜 이후 재크롤링 확인', report)

    def test_missing_crawl_data_is_not_reported_as_unindexed(self):
        from seo.search_console_monitor import crawl_after_significant_change
        report = crawl_after_significant_change([], {'/directory': '2026-11-07'})
        self.assertIn('조회 결과 없음 · 재크롤링 여부 불명', report)
        report = crawl_after_significant_change(
            [{'url': 'https://linkwiki.info/directory'}],
            {'/directory': '2026-11-07'})
        self.assertIn('크롤링 시점 미제공 · 재크롤링 여부 불명', report)
        self.assertNotIn('색인 실패', report)

    def test_google_index_diagnostics_keep_actual_blocking_fields(self):
        from seo.search_console_monitor import technical_index_obstacles, technical_index_diagnostic
        blocked = {'url': 'https://linkwiki.info/directory', 'verdict': 'NEUTRAL',
                   'coverage': 'Crawled - currently not indexed', 'robots_state': 'ALLOWED',
                   'indexing_state': 'BLOCKED_BY_HTTP_HEADER', 'fetch_state': 'SUCCESSFUL',
                   'user_canonical': 'https://linkwiki.info/directory',
                   'google_canonical': ''}
        self.assertIn('Google HTTP X-Robots-Tag noindex 확인', technical_index_obstacles(blocked))
        report = technical_index_diagnostic([blocked])
        self.assertIn('BLOCKED_BY_HTTP_HEADER', report)
        self.assertIn('Google HTTP X-Robots-Tag noindex 확인', report)
        self.assertIn('미조회', report)

    def test_unknown_google_url_does_not_claim_no_technical_block(self):
        unknown = {
            'url': 'https://linkwiki.info/categories/community',
            'verdict': 'NEUTRAL',
            'coverage': 'Google에는 아직 알려지지 않은 URL입니다.',
            'robots_state': 'ROBOTS_TXT_STATE_UNSPECIFIED',
            'indexing_state': 'INDEXING_STATE_UNSPECIFIED',
            'fetch_state': 'PAGE_FETCH_STATE_UNSPECIFIED',
        }
        out = monitor.technical_index_diagnostic([unknown])
        self.assertIn('Google 크롤링·색인 기술 정보 미제공', out)
        self.assertIn('차단이 없다고 판단할 수 없습니다', out)
        self.assertNotIn('명시적인 기술 차단 신호가 확인되지 않았습니다', out)

    def test_crawled_not_indexed_with_confirmed_allowed_fetch_has_distinct_diagnosis(self):
        crawled = {
            'url': 'https://linkwiki.info/directory',
            'verdict': 'NEUTRAL',
            'coverage': '크롤링됨 - 현재 색인이 생성되지 않음',
            'robots_state': 'ALLOWED', 'indexing_state': 'INDEXING_ALLOWED',
            'fetch_state': 'SUCCESSFUL', 'last_crawl': '2026-11-08T08:29:34Z',
            'user_canonical': 'https://linkwiki.info/directory',
            'google_canonical': 'https://linkwiki.info/directory',
        }
        out = monitor.technical_index_diagnostic([crawled])
        self.assertIn('저장된 크롤링 정보에서 명시적 차단은 보이지 않습니다', out)
        self.assertNotIn('Google 크롤링·색인 기술 정보 미제공', out)

    def test_gsc_search_impressions_are_not_erased_by_stale_url_inspection(self):
        pages = [
            {'keys': ['https://linkwiki.info/guides/address-check'],
             'impressions': 3, 'clicks': 1},
            {'keys': ['https://linkwiki.info/'],
             'impressions': 72, 'clicks': 26},
            {'keys': ['https://linkwiki.info/directory'],
             'impressions': 0, 'clicks': 0},
        ]
        inspections = [
            {'url': 'https://linkwiki.info/guides/address-check',
             'verdict': 'NEUTRAL', 'coverage': '크롤링됨 - 현재 색인이 생성되지 않음',
             'last_crawl': '2026-10-19T06:04:57Z'},
            {'url': 'https://linkwiki.info/', 'verdict': 'PASS'},
            {'url': 'https://linkwiki.info/directory',
             'verdict': 'NEUTRAL', 'coverage': 'Crawled - currently not indexed'},
        ]
        differences = monitor.compare_search_visibility_with_inspection(
            pages, inspections, '2026-11-06')
        self.assertEqual(len(differences), 1)
        self.assertEqual(differences[0]['impressions'], 3)
        self.assertEqual(differences[0]['url'],
                         'https://linkwiki.info/guides/address-check')
        report = monitor.format_search_visibility_inspection_conflicts(
            pages, inspections, '2026-11-06')
        self.assertIn('https://linkwiki.info/guides/address-check', report)
        self.assertNotIn('| https://linkwiki.info/directory |', report)
        self.assertIn("|---|---:|---:|---|---|", report)
        self.assertNotIn("LITERAL_BACKSLASH_N_SENTINEL", report)

    def test_visibility_inspection_failure_does_not_claim_empty_result(self):
        report = monitor.format_search_visibility_inspection_conflicts(
            [], [], '2026-11-06', 'HTTPError HTTP 403')
        self.assertIn('URL 검사 조회 실패', report)
        self.assertNotIn('불일치 관측 없음', report)

    def test_robots_fetch_and_canonical_have_distinct_diagnoses(self):
        from seo.search_console_monitor import technical_index_obstacles
        problems = technical_index_obstacles({
            'robots_state': 'DISALLOWED', 'indexing_state': 'BLOCKED_BY_META_TAG',
            'fetch_state': 'SOFT_404', 'user_canonical': 'https://linkwiki.info/directory',
            'google_canonical': 'https://linkwiki.info/'})
        self.assertIn('Google robots.txt 차단 확인', problems)
        self.assertIn('Google HTML noindex 확인', problems)
        self.assertIn('Google 페이지 가져오기: SOFT_404', problems)
        self.assertTrue(any('canonical' in item for item in problems))
        self.assertEqual(technical_index_obstacles({
            'robots_state': 'ALLOWED', 'indexing_state': 'INDEXING_ALLOWED',
            'fetch_state': 'SUCCESSFUL', 'google_canonical': '',
            'user_canonical': 'https://linkwiki.info/directory'}), [])

    def test_technical_blocker_takes_priority_over_generic_content_advice(self):
        row = {'url': 'https://linkwiki.info/directory', 'verdict': 'NEUTRAL',
               'coverage': 'Crawled - currently not indexed',
               'robots_state': 'DISALLOWED'}
        report = monitor.priority_index_checks([row])
        self.assertIn('Google robots.txt 차단 확인', report)

    def test_branded_and_generic_search_are_separated_without_guessing(self):
        rows = [
            {'keys': ['링크위키'], 'impressions': 14, 'clicks': 8, 'position': 2},
            {'keys': ['링크 - 위키'], 'impressions': 2, 'clicks': 1, 'position': 3},
            {'keys': ['주소 위키'], 'impressions': 8, 'clicks': 1, 'position': 10},
            {'keys': ['주소모음'], 'impressions': 1, 'clicks': 1, 'position': 111},
        ]
        groups = monitor.brand_vs_nonbrand_rows(rows)
        self.assertEqual(groups[0]['name'], '브랜드 검색')
        self.assertEqual((groups[0]['impressions'], groups[0]['clicks']), (16, 9))
        self.assertEqual(groups[1]['name'], '일반 검색')
        self.assertEqual((groups[1]['impressions'], groups[1]['clicks']), (9, 2))
        report = monitor.format_report(rows, [], '2026-10-04', '2026-10-31',
                                       'sc-domain:linkwiki.info')
        self.assertIn('| 브랜드 검색 | 16 | 9 | 2.1 |', report)
        self.assertIn('| 일반 검색 | 9 | 2 | 21.2 |', report)
        self.assertLess(report.index('## 브랜드 검색과 일반 검색'),
                        report.index('## 검색어 상위 30개'))
        self.assertIn('비공개·익명 검색어', report)


    def test_priority_index_checks_distinguish_missing_from_unindexed(self):
        rows = [
            {'url': 'https://linkwiki.info/', 'verdict': 'PASS',
             'google_canonical': 'https://linkwiki.info/'},
            {'url': 'https://linkwiki.info/directory', 'verdict': 'NEUTRAL',
             'coverage': 'URL is unknown to Google'},
        ]
        report = monitor.priority_index_checks(rows)
        self.assertIn('https://linkwiki.info/directory | 핵심 주소모음 목록 | NEUTRAL', report)
        self.assertIn('사이트맵 제출·홈페이지 내부 링크', report)
        self.assertIn('https://linkwiki.info/categories/ | 카테고리 허브 | 조회 결과 없음', report)
        self.assertIn('조회 결과가 없다는 사실은 Google 미발견', report)
        self.assertNotIn('https://linkwiki.info/categories/ | 카테고리 허브 | NEUTRAL', report)

    def test_priority_index_checks_detect_google_canonical_mismatch(self):
        report = monitor.priority_index_checks([{
            'url': 'https://linkwiki.info/directory', 'verdict': 'PASS',
            'google_canonical': 'https://linkwiki.info/',
        }])
        self.assertIn('Google 선택 정규 URL과 사이트 canonical 차이 검토', report)

    def test_report_search_query_table_remains_contiguous(self):
        report = monitor.format_report(
            [{'keys': ['주소모음'], 'impressions': 2, 'clicks': 1,
              'ctr': .5, 'position': 11}], [],
            '2026-10-01', '2026-10-28', 'sc-domain:linkwiki.info',
            date_rows=[{'keys': ['2026-10-28'], 'impressions': 2,
                        'clicks': 1, 'position': 11}])
        expected = ('## 검색어 상위 30개\n\n'
                    '| 검색어 | 노출 | 클릭 | CTR | 평균 순위 |\n'
                    '|---|---:|---:|---:|---:|\n'
                    '| 주소모음 | 2 | 1 | 50.0% | 11.0 |')
        self.assertIn(expected, report)
        self.assertLess(report.index('## 전체 검색 성과'),
                        report.index('## 최근 7일과 직전 7일 비교'))
        self.assertLess(report.index('## 최근 7일과 직전 7일 비교'),
                        report.index('## 검색어 상위 30개'))

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

    def test_core_family_aggregates_exact_vs_longtail_without_inflating_rank(self):
        rows = [
            {"keys": ["주소모음"], "impressions": 1, "clicks": 1, "position": 111.0},
            {"keys": ["주소 모음"], "impressions": 1, "clicks": 0, "position": 90.0},
            {"keys": ["주소모음 위키"], "impressions": 4, "clicks": 1, "position": 6.0},
            {"keys": ["링크모음"], "impressions": 3, "clicks": 0, "position": 123.0},
            {"keys": ["링크모음 웹사이트"], "impressions": 2, "clicks": 0, "position": 144.5},
            {"keys": ["주소모음 링크모음"], "impressions": 2, "clicks": 0, "position": 30.0},
            {"keys": ["링크위키"], "impressions": 40, "clicks": 15, "position": 2.0},
        ]
        result = {item["keyword"]: item for item in monitor.core_family_keyword_rows(rows)}
        self.assertEqual(result["주소모음"]["exact"]["impressions"], 2)
        self.assertEqual(result["주소모음"]["exact"]["position"], 100.5)
        self.assertEqual(result["주소모음"]["related"]["impressions"], 6)
        self.assertEqual(result["주소모음"]["related"]["position"], 14.0)
        self.assertEqual(result["링크모음"]["related"]["impressions"], 2)
        self.assertFalse(result["사이트모음"]["exact"]["observed"])
        self.assertEqual(sum(item[part]["impressions"] for item in result.values()
                             for part in ("exact", "related")), 13)
        formatted = monitor.format_core_family_keyword_report(rows)
        self.assertIn("100.5", formatted)
        self.assertIn("관측 없음", formatted)

    def test_core_family_filter_is_unanchored_but_exact_filter_stays_anchored(self):
        self.assertFalse(monitor.FAMILY_QUERY_FILTERS[0]["filters"][0]["expression"].startswith("^"))
        self.assertTrue(monitor.CORE_QUERY_FILTERS[0]["filters"][0]["expression"].startswith("^"))

    def test_core_family_failed_query_is_not_reported_as_zero(self):
        output = monitor.format_core_family_keyword_report([], "HTTPError HTTP 403")
        self.assertIn("조회 오류", output)
        self.assertNotIn("| 사이트모음 | 관측 없음", output)

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

    def test_exact_core_keyword_landing_is_prioritized_over_unrelated_impressions(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content").mkdir()
            for day in ("20261108", "20261109", "20261110"):
                (root / "content" / f"seo-{day}-topic.md").write_text("# test", encoding="utf-8")
            ordinary = [
                {"keys": [f"https://linkwiki.info/guides/ordinary-{i}"],
                 "impressions": 100 - i} for i in range(8)
            ]
            exact = [
                {"keys": ["주소모음", "https://linkwiki.info/guides/address-check"],
                 "impressions": 5},
                {"keys": ["링크모음", "https://linkwiki.info/guides/choose-directory"],
                 "impressions": 3},
                {"keys": ["사이트모음", "https://linkwiki.info/guides/security"],
                 "impressions": 2},
            ]
            with patch.object(monitor, "ROOT", root):
                targets = monitor.inspection_targets(ordinary, limit=18, core_query_pages=exact)
        self.assertIn("https://linkwiki.info/guides/choose-directory", targets)
        self.assertIn("https://linkwiki.info/guides/security", targets)
        self.assertNotIn("https://linkwiki.info/guides/ordinary-0", targets)
        self.assertLessEqual(len(targets), 20)

    def test_exact_keyword_inspection_rejects_unrelated_and_offsite_rows(self):
        rows = [
            {"keys": ["주소모음", "https://outside.example/landing"], "impressions": 40},
            {"keys": ["링크모음 사이트", "https://linkwiki.info/guides/irrelevant"], "impressions": 30},
            {"keys": ["사이트 모음", "https://linkwiki.info/guides/link-faq.html"], "impressions": 7},
        ]
        targets = monitor.inspection_targets([], core_query_pages=rows)
        self.assertIn("https://linkwiki.info/guides/link-faq", targets)
        self.assertIn("https://linkwiki.info/guides/link-faq.html", targets)
        self.assertNotIn("https://linkwiki.info/guides/irrelevant", targets)
        self.assertNotIn("https://outside.example/landing", targets)

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
        self.assertLessEqual(len(targets), 20)

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
        self.assertLessEqual(len(targets), 20)

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


    def test_core_landing_page_split_uses_only_observed_site_rows(self):
        rows = [
            {'keys': ['주소모음', 'https://linkwiki.info/directory'],
             'impressions': 7, 'clicks': 2, 'position': 12.4},
            {'keys': ['링크 모음', 'https://linkwiki.info/'],
             'impressions': 3, 'clicks': 0, 'position': 22.0},
            {'keys': ['사이트모음', 'https://other.example/'],
             'impressions': 10, 'clicks': 3, 'position': 1.0},
        ]
        report = monitor.format_core_landing_page_split(rows)
        self.assertIn('| 주소모음 | https://linkwiki.info/directory | 7 | 2 | 12.4 |', report)
        self.assertIn('| 링크모음 | https://linkwiki.info/ | 3 | 0 | 22.0 |', report)
        self.assertNotIn('other.example', report)
        self.assertIn('관측된 URL이 여러 개여도', report)

    def test_core_landing_page_split_handles_absent_rows(self):
        report = monitor.format_core_landing_page_split([])
        self.assertIn('관측된 검색어·페이지 조합 없음', report)


if __name__ == '__main__':
    unittest.main()
