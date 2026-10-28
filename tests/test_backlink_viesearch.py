import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seo import backlink_viesearch as adapter
from seo import backlink_manager as ledger


class SubmitTests(unittest.TestCase):
    def test_valid_api_payload_and_success(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return None
        response = FakeResponse()
        with patch.object(adapter.urllib.request, "urlopen", return_value=response) as network:
            with patch.object(adapter.json, "load", return_value={"success": True, "token": "pending_123"}):
                result = adapter.submit("fake_test_key", {"url": "https://linkwiki.info/"})
        self.assertEqual(result["success"], True)
        self.assertEqual(network.call_args.args[0].full_url, adapter.API)

    def test_existing_submission_skip_before_key_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reg.json"
            reg = ledger.load_registry(path)
            reg["entries"].append({"platform": "Viesearch", "submission_status": "pending_review"})
            ledger.save_registry(path, reg)
            output = io.StringIO()
            with patch("sys.argv", ["prog", "--registry", str(path), "--execute"]):
                with contextlib.redirect_stdout(output):
                    adapter.main()
            self.assertIn("SKIP", output.getvalue())

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "registry.json"
            out = io.StringIO()
            with patch("sys.argv", ["prog", "--registry", str(path)]):
                with contextlib.redirect_stdout(out):
                    adapter.main()
            self.assertIn('"dry_run": true', out.getvalue())
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
