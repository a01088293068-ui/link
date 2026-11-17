import unittest

from seo.indexnow_notify import (
    SITE, changed_page_urls, public_path_for_source, sitemap_urls,
)

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def sitemap(*urls):
    return ('<urlset xmlns="' + NS + '">' +
            ''.join('<url><loc>' + url + '</loc></url>' for url in urls) +
            '</urlset>').encode()


class IndexNowNotifyTests(unittest.TestCase):
    def setUp(self):
        self.available = {
            SITE + "/",
            SITE + "/directory",
            SITE + "/categories/",
            SITE + "/categories/community",
            SITE + "/categories/ai",
            SITE + "/guides/security",
            SITE + "/blog/",
            SITE + "/blog/new-guide/",
        }

    def test_maps_clean_public_paths(self):
        self.assertEqual(public_path_for_source("index.html"), SITE + "/")
        self.assertEqual(public_path_for_source("directory.html"), SITE + "/directory")
        self.assertEqual(public_path_for_source("categories/community.html"),
                         SITE + "/categories/community")
        self.assertEqual(public_path_for_source("guides/security.html"),
                         SITE + "/guides/security")
        self.assertEqual(public_path_for_source("content/new-guide.md"),
                         SITE + "/blog/new-guide/")

    def test_catalog_change_notifies_home_directory_and_category_hubs(self):
        urls = changed_page_urls(["assets/verified-directory.json"], self.available)
        self.assertEqual(urls, sorted([
            SITE + "/", SITE + "/directory", SITE + "/categories/",
            SITE + "/categories/community", SITE + "/categories/ai",
        ]))
        self.assertNotIn(SITE + "/guides/security", urls)

    def test_article_change_notifies_article_and_discovery_hubs(self):
        urls = changed_page_urls(["content/new-guide.md"], self.available)
        self.assertEqual(urls, sorted([
            SITE + "/", SITE + "/blog/", SITE + "/blog/new-guide/",
        ]))

    def test_build_change_notifies_only_urls_in_current_sitemap(self):
        urls = changed_page_urls(["build.py"], self.available)
        self.assertEqual(urls, sorted(self.available))

    def test_unrelated_file_does_not_create_fake_notifications(self):
        self.assertEqual(changed_page_urls(["README.md", "seo/rank-history.json"],
                                           self.available), [])

    def test_sitemap_source_html_paths_normalize_to_clean_canonicals(self):
        self.assertEqual(sitemap_urls(sitemap(SITE + "/directory.html",
                                              SITE + "/categories/index.html")),
                         {SITE + "/directory", SITE + "/categories/"})

    def test_sitemap_rejects_external_and_query_urls(self):
        with self.assertRaises(ValueError):
            sitemap_urls(sitemap("https://example.com/"))
        with self.assertRaises(ValueError):
            sitemap_urls(sitemap(SITE + "/directory?preview=1"))

    def test_sitemap_rejects_duplicates_after_normalization(self):
        with self.assertRaises(ValueError):
            sitemap_urls(sitemap(SITE + "/directory.html", SITE + "/directory"))

    def test_sitemap_accepts_canonical_urls(self):
        self.assertEqual(sitemap_urls(sitemap(SITE + "/", SITE + "/directory")),
                         {SITE + "/", SITE + "/directory"})


if __name__ == "__main__":
    unittest.main()
