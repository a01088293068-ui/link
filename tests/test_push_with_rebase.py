"""Exercise the exact shared Git push retry shell script without network."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "seo/push_with_rebase.sh"


class SafePushTests(unittest.TestCase):
    def run_case(self, fail_count=0, rebase_fail=False):
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            fake_git = folder / "git"
            fake_git.write_text(
                '#!/usr/bin/env bash\n'
                'echo "$*" >> "$FAKE_GIT_LOG"\n'
                'if [[ "$1" == "push" ]]; then\n'
                '  count=0\n'
                '  if [[ -f "$FAKE_PUSH_COUNT" ]]; then read -r count < "$FAKE_PUSH_COUNT"; fi\n'
                '  count=$((count + 1))\n'
                '  echo "$count" > "$FAKE_PUSH_COUNT"\n'
                '  if (( count <= FAKE_FAIL_COUNT )); then exit 1; fi\n'
                'fi\n'
                'if [[ "$1" == "rebase" && "$2" != "--abort" && "$FAKE_REBASE_FAIL" == 1 ]]; then exit 1; fi\n'
                'exit 0\n',
                encoding="utf-8")
            fake_git.chmod(0o755)
            logfile = folder / "calls.log"
            env = dict(os.environ, PATH=str(folder) + os.pathsep + os.environ["PATH"],
                       FAKE_GIT_LOG=str(logfile),
                       FAKE_PUSH_COUNT=str(folder / "push.count"),
                       FAKE_FAIL_COUNT=str(fail_count),
                       FAKE_REBASE_FAIL="1" if rebase_fail else "0")
            result = subprocess.run(["bash", str(SCRIPT)], env=env,
                                    capture_output=True, text=True, timeout=15)
            calls = logfile.read_text(encoding="utf-8").splitlines()
            return result, calls

    def test_initial_push_success(self):
        result, calls = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["push origin HEAD:main"])

    def test_rebase_retry_then_success(self):
        result, calls = self.run_case(fail_count=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["push origin HEAD:main", "fetch origin main",
                                 "rebase origin/main", "push origin HEAD:main"])

    def test_conflicting_rebase_never_force_pushes(self):
        result, calls = self.run_case(fail_count=1, rebase_fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rebase --abort", calls)
        self.assertEqual(calls.count("push origin HEAD:main"), 1)
        self.assertFalse(any("--force" in item for item in calls))

    def test_three_rejected_pushes_fail_without_force(self):
        result, calls = self.run_case(fail_count=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls.count("push origin HEAD:main"), 3)
        self.assertFalse(any("--force" in item for item in calls))


if __name__ == "__main__":
    unittest.main()
