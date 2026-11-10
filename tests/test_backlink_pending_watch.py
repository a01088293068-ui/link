"""Read-only pending link detection: no search result can auto-approve a listing."""
import unittest
from seo import backlink_pending_watch as watch


def registry():
    return {"target_domain": "linkwiki.info", "entries": [
        {"platform": "GainWeb", "submission_status": "pending_review",
         "submission_url": "https://gainweb.org/submit.php", "public_url": ""},
        {"platform": "Viesearch", "submission_status": "pending_review",
         "submission_url": "https://viesearch.com/plan", "public_url": ""},
        {"platform": "Archive intermediary", "submission_status": "pending_review",
         "submission_url": "https://freewebsubmission.com/submit", "public_url": ""},
        {"platform": "Already public", "submission_status": "approved",
         "submission_url": "https://public.example/submit", "public_url": "https://public.example/a"},
        {"platform": "Already checked", "submission_status": "pending_review",
         "submission_url": "https://existing.example/submit",
         "public_url": "https://existing.example/public"},
    ]}


class PendingBacklinkTests(unittest.TestCase):
    def test_only_eligible_pending_domains_without_public_url(self):
        self.assertEqual(watch.pending_hosts(registry()), {
            "gainweb.org": "GainWeb", "viesearch.com": "Viesearch"})

    def test_filters_search_pages_cross_domain_and_submission_pages(self):
        for url in ("https://another.org/listing/linkwiki",
                    "http://gainweb.org/linkwiki",
                    "https://gainweb.org/submit.php",
                    "https://gainweb.org/search?q=linkwiki",
                    "https://gainweb.org/listing?url=linkwiki",
                    "https://gainweb.org/"):
            with self.subTest(url=url):
                self.assertEqual(watch.candidate_url({"link": url}, "gainweb.org"), "")
        self.assertEqual(watch.candidate_url(
            {"link": "https://gainweb.org/links/linkwiki"}, "gainweb.org"),
            "https://gainweb.org/links/linkwiki")

    def test_actual_direct_link_requires_live_html_not_search_snippet(self):
        def search(host):
            return [{"link": "https://" + host + "/sites/linkwiki",
                     "snippet": "linkwiki.info is linked here"}]
        def fetch(url):
            if "gainweb" in url:
                return 200, ('<meta name="robots" content="index,follow">'
                             '<a href="https://linkwiki.info/">LinkWiki</a>'), "", "text/html"
            return 200, '<p>linkwiki.info</p>', "", "text/html"
        r = watch.inspect(registry(), search, fetch)
        self.assertEqual(r["confirmed_domains"], ["gainweb.org"])
        self.assertEqual(r["submitted_new"], 0)
        self.assertEqual(len(r["checked_pages"]), 2)
        self.assertEqual(r["checked_pages"][1]["result"], "missing_link")

    def test_nofollow_direct_href_counts_as_link_without_rating_claim(self):
        r = watch.inspect(registry(),
                          lambda host: [{"link": "https://" + host + "/listing/linkwiki"}],
                          lambda url: (200, '<a href="https://linkwiki.info" rel="ugc nofollow">Visit</a>',
                                       "", "text/html"))
        self.assertEqual(len(r["confirmed_domains"]), 2)
        self.assertTrue(all(x["result"] == "link_with_rel" for x in r["checked_pages"]))

    def test_noindex_is_not_public_verified_domain(self):
        r = watch.inspect(registry(),
                          lambda host: [{"link": "https://" + host + "/listing/linkwiki"}],
                          lambda url: (200, '<meta name="robots" content="noindex">'
                                       '<a href="https://linkwiki.info">Visit</a>',
                                       "", "text/html"))
        self.assertEqual(r["confirmed_domains"], [])
        self.assertTrue(all(x["result"] == "noindex" for x in r["checked_pages"]))

    def test_missing_results_do_not_mean_rejection(self):
        r = watch.inspect(registry(), lambda host: [], lambda _: (_ for _ in ()).throw(
            AssertionError("no fetching without candidates")))
        self.assertEqual(r["confirmed_domains"], [])
        self.assertIn("NOT proof of rejection", watch.report(r))
        self.assertIn("No new form submissions", watch.report(r))


if __name__ == "__main__":
    unittest.main()
