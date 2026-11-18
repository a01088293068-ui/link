from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DirectoryMetadataTests(unittest.TestCase):
    def test_social_metadata_matches_directory_page_intent(self):
        html = (ROOT / "directory.html").read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", html)
        description = re.search(r'<meta content="([^"]+)" name="description"/>', html)
        og_title = re.search(r'<meta content="([^"]+)" property="og:title"/>', html)
        twitter_title = re.search(r'<meta content="([^"]+)" name="twitter:title"/>', html)
        og_description = re.search(r'<meta content="([^"]+)" property="og:description"/>', html)
        twitter_description = re.search(r'<meta content="([^"]+)" name="twitter:description"/>', html)
        self.assertIsNotNone(title)
        self.assertIsNotNone(description)
        self.assertIsNotNone(og_title)
        self.assertIsNotNone(twitter_title)
        self.assertIsNotNone(og_description)
        self.assertIsNotNone(twitter_description)
        self.assertEqual(og_title.group(1), title.group(1))
        self.assertEqual(twitter_title.group(1), title.group(1))
        self.assertEqual(og_description.group(1), description.group(1))
        self.assertEqual(twitter_description.group(1), description.group(1))
        self.assertIn("사이트모음", title.group(1))
        self.assertIn("사이트모음", html.split("</head>", 1)[1].split("</h1>", 1)[0])
        self.assertIn('href="https://linkwiki.info/directory" rel="canonical"', html)
        self.assertNotIn("주소모음 전체 검색 |", og_title.group(1))


if __name__ == "__main__":
    unittest.main()
