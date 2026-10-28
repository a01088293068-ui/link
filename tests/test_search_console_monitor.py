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

    def test_empty_report(self):
        result = monitor.format_report([], [], '2026-09-01', '2026-09-28', 'sc-domain:linkwiki.info')
        self.assertIn('데이터 없음', result)

    def test_report_values(self):
        rows = [{'keys': ['주소모음'], 'impressions': 100, 'clicks': 3, 'ctr': .03, 'position': 9.8}]
        result = monitor.format_report(rows, [], '2026-09-01', '2026-09-28', 'sc-domain:linkwiki.info')
        self.assertIn('주소모음 | 100 | 3 | 3.0% | 9.8', result)


if __name__ == '__main__':
    unittest.main()
