"""Regression tests for Cloudflare Pages' public build input allowlist."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build import PUBLIC_SOURCE_DIRS, PUBLIC_SOURCE_FILES, copy_public_sources


class PublicBuildAllowlistTests(unittest.TestCase):
    def make_source(self, root):
        for name in PUBLIC_SOURCE_DIRS:
            folder = root / name
            folder.mkdir(parents=True)
            (folder / "public.txt").write_text("visible", encoding="utf-8")
        for name in PUBLIC_SOURCE_FILES:
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("public", encoding="utf-8")

    def test_dependency_html_is_not_published_or_audited(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source", root / "dist"
            source.mkdir()
            output.mkdir()
            self.make_source(source)
            private = source / "node_modules/playwright-core/lib/vite/htmlReport"
            private.mkdir(parents=True)
            (private / "index.html").write_text("<html>tool report</html>", encoding="utf-8")
            (source / ".env").write_text("not-for-publication", encoding="utf-8")
            (source / "tests").mkdir()
            (source / "tests/test.html").write_text("private", encoding="utf-8")
            copy_public_sources(source, output)
            self.assertFalse((output / "node_modules").exists())
            self.assertFalse((output / ".env").exists())
            self.assertFalse((output / "tests").exists())
            for name in PUBLIC_SOURCE_DIRS + PUBLIC_SOURCE_FILES:
                self.assertTrue((output / name).exists(), name)

    def test_missing_public_source_fails_closed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source", root / "dist"
            source.mkdir()
            output.mkdir()
            self.make_source(source)
            (source / "index.html").unlink()
            with self.assertRaisesRegex(RuntimeError, "Required public source file"):
                copy_public_sources(source, output)


if __name__ == "__main__":
    unittest.main()
