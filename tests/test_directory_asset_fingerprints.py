"""Directory JavaScript URLs must refresh when bytes change, never by build date."""
import hashlib
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build import fingerprint_directory_scripts

NAMES = ("directory-search.js", "directory.js", "mobile-menu.js", "address-inspector.js")


class DirectoryAssetFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in NAMES:
            (self.root / name).write_text("console.log('"+name+"')", encoding="utf-8")
        self.html = "".join(
            '<script defer src="assets/' + name + '?v=old"></script>'
            for name in NAMES[:3]
        ) + '<script defer src="/assets/address-inspector.js"></script>'

    def test_each_script_gets_digest_from_actual_file(self):
        result = fingerprint_directory_scripts(self.html, self.root)
        for name in NAMES:
            digest = hashlib.sha256((self.root / name).read_bytes()).hexdigest()[:12]
            self.assertIn("assets/" + name + "?v=" + digest, result)
            self.assertNotIn("assets/" + name + "?v=old", result)

    def test_rebuild_is_stable_and_changed_script_alone_rotates(self):
        original = fingerprint_directory_scripts(self.html, self.root)
        self.assertEqual(fingerprint_directory_scripts(original, self.root), original)
        (self.root / "directory.js").write_text("console.log('changed')", encoding="utf-8")
        updated = fingerprint_directory_scripts(original, self.root)
        self.assertNotEqual(original, updated)
        for name in ("directory-search.js", "mobile-menu.js", "address-inspector.js"):
            pattern = r"assets/" + re.escape(name) + r"\\?v=([a-f0-9]{12})"
            self.assertEqual(re.search(pattern, original).group(1),
                             re.search(pattern, updated).group(1))

    def test_missing_asset_or_reference_fails_build(self):
        (self.root / "directory-search.js").unlink()
        with self.assertRaisesRegex(RuntimeError, "Missing directory browser asset"):
            fingerprint_directory_scripts(self.html, self.root)
        (self.root / "directory-search.js").write_text("restored", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Expected one directory script reference"):
            fingerprint_directory_scripts(self.html.replace("assets/directory.js", "assets/missing.js"),
                                          self.root)


if __name__ == "__main__":
    unittest.main()
