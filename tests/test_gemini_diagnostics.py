import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "seo" / "check_gemini_models.py"
spec = importlib.util.spec_from_file_location("diagnostics_test", SCRIPT)
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class DiagnosticTests(unittest.TestCase):
    def test_reports_working_model(self):
        responses = [({"models": [{"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]}]}, "OK"),
                     ({"candidates": [{"content": {"parts": [{"text": "확인"}]}}]}, "OK"),
                     (None, "HTTP 503"), (None, "HTTP 503")]
        with patch.object(diagnostics, "request_json", side_effect=responses):
            self.assertTrue(diagnostics.diagnose("dummy"))

    def test_no_working_model(self):
        with patch.object(diagnostics, "request_json", return_value=(None, "HTTP 503")):
            self.assertFalse(diagnostics.diagnose("dummy"))

    def test_list_only_is_not_sufficient(self):
        with patch.object(diagnostics, "request_json", side_effect=[({"models": []}, "OK")] + [(None, "HTTP 429")] * 3):
            self.assertFalse(diagnostics.diagnose("dummy"))


if __name__ == "__main__":
    unittest.main()
