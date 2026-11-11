"""Regression: Cloudflare's npm-installed Playwright assets must never ship."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build import PUBLIC_SOURCE_FILES, PUBLIC_SOURCE_DIRS, copy_public_sources


class PublicSourceAllowlistTests(unittest.TestCase):
    def test_build_ignores_node_modules_and_private_directories(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / "source", root / "dist"
            source.mkdir()
            output.mkdir()
            for name in PUBLIC_SOURCE_DIRS:
                folder = source / name
                folder.mkdir()
                (folder / "public-marker.txt").write_text(name, encoding="utf-8")
            for name in PUBLIC_SOURCE_FILES:
                (source / name).write_text(name, encoding="utf-8")

            for unwanted in ("node_modules/playwright-core/lib/vite/traceViewer",
                             ".git/objects", "tools", "tests", "seo", "content",
                             ".venv/lib"):
                path = source / unwanted
                path.mkdir(parents=True)
                (path / "index.html").write_text("<html>private</html>", encoding="utf-8")
            (source / "package.json").write_text('{"private":true}', encoding="utf-8")
            (source / ".env").write_text("SHOULD_NOT_COPY=1", encoding="utf-8")

            copy_public_sources(source, output)

            self.assertEqual({child.name for child in output.iterdir()},
                             set(PUBLIC_SOURCE_DIRS) | set(PUBLIC_SOURCE_FILES))
            self.assertFalse((output / "node_modules").exists())
            self.assertFalse((output / "tools").exists())
            self.assertFalse((output / ".env").exists())
            self.assertFalse((output / "package.json").exists())
            self.assertTrue((output / "assets/public-marker.txt").is_file())
            self.assertTrue((output / "_redirects").is_file())

    def test_required_public_asset_missing_fails_instead_of_partial_release(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / "source", root / "dist"
            source.mkdir()
            output.mkdir()
            for name in PUBLIC_SOURCE_DIRS:
                (source / name).mkdir()
            for name in PUBLIC_SOURCE_FILES:
                if name != "_headers":
                    (source / name).write_text("data", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Required public source file"):
                copy_public_sources(source, output)


if __name__ == "__main__":
    unittest.main()
