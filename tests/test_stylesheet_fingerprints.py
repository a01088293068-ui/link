"""Public stylesheet URLs are fingerprinted from their actual bytes."""
import hashlib
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build import fingerprint_stylesheets


class StylesheetFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "style.css").write_text("body { color: black; }", encoding="utf-8")
        (self.root / "blog.css").write_text(".blog { display: block; }", encoding="utf-8")

    def test_each_referenced_stylesheet_uses_content_digest(self):
        html = (
            '<link rel="stylesheet" href="/assets/style.css?v=old">'
            '<link rel="stylesheet" href="../assets/blog.css">'
        )
        result = fingerprint_stylesheets(html, self.root)
        for name in ("style.css", "blog.css"):
            digest = hashlib.sha256((self.root / name).read_bytes()).hexdigest()[:12]
            self.assertIn(f"assets/{name}?v={digest}", result)
        self.assertNotIn("?v=old", result)

    def test_rebuild_is_stable_and_only_changed_stylesheet_rotates(self):
        html = '<link href="/assets/style.css"><link href="/assets/blog.css?v=old">'
        original = fingerprint_stylesheets(html, self.root)
        self.assertEqual(fingerprint_stylesheets(original, self.root), original)
        old_blog = re.search(r"blog\.css\?v=([a-f0-9]{12})", original).group(1)
        (self.root / "style.css").write_text("body { color: navy; }", encoding="utf-8")
        updated = fingerprint_stylesheets(original, self.root)
        new_style = re.search(r"style\.css\?v=([a-f0-9]{12})", updated).group(1)
        new_blog = re.search(r"blog\.css\?v=([a-f0-9]{12})", updated).group(1)
        self.assertNotEqual(
            new_style,
            re.search(r"style\.css\?v=([a-f0-9]{12})", original).group(1),
        )
        self.assertEqual(old_blog, new_blog)

    def test_missing_stylesheet_fails_build(self):
        (self.root / "blog.css").unlink()
        with self.assertRaisesRegex(RuntimeError, "Missing public stylesheet"):
            fingerprint_stylesheets('<link href="/assets/style.css">', self.root)


if __name__ == "__main__":
    unittest.main()
