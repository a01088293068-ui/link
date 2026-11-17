"""Regression tests for post-build public release parity monitoring."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "cloudflare-live-release-check.yml"


class LiveReleaseWorkflowTests(unittest.TestCase):
    def test_parity_check_runs_after_successful_main_push_quality_gate(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflows: ['LinkWiki SEO build and consistency gate']", source)
        self.assertIn("branches: [main]", source)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", source)
        self.assertIn("github.event.workflow_run.event == 'push'", source)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha }}", source)

    def test_parity_check_rebuilds_and_checks_public_release_without_write_credentials(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", source)
        self.assertIn("python3 -B build.py", source)
        self.assertIn("seo/live_release_check.py --dist dist", source)
        self.assertNotIn("CLOUDFLARE_API_TOKEN", source)
        self.assertNotIn("GITHUB_TOKEN", source)

    def test_existing_release_checker_compares_real_directory_counts_and_cards(self):
        checker = (ROOT / "seo" / "live_release_check.py").read_text(encoding="utf-8")
        self.assertIn("deployed visible site counts differ from generated build", checker)
        self.assertIn("deployed site cards differ from generated build", checker)
        self.assertIn("deployed canonical differs or is duplicated", checker)
        self.assertIn("check_crawl_files", checker)


if __name__ == "__main__":
    unittest.main()
