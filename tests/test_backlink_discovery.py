import unittest
from seo import backlink_discovery as discovery


class BacklinkDiscoveryTests(unittest.TestCase):
    def test_hostname_and_prohibited_hosts(self):
        self.assertEqual(discovery.hostname("https://www.example.org/submit"), "example.org")
        self.assertEqual(discovery.hostname("http://example.org"), "")
        self.assertIsNone(discovery.assess({
            "link": "https://www.google.com/search", "title": "Submit website",
            "snippet": "editorial website directory"
        }, set()))

    def test_remove_duplicates_and_suspicious_offers(self):
        registry = {"entries": [
            {"submission_url": "https://known.example.org/add", "public_url": ""}
        ]}
        results = [
            {"link": "https://known.example.org/new", "title": "Submit Website",
             "snippet": "Editorial website directory listing"},
            {"link": "https://good.example.org/submit", "title": "Submit website",
             "snippet": "Curated web directory editorial listing"},
            {"link": "https://spam.example.org", "title": "Buy backlinks",
             "snippet": "Submit websites to 1000 directories"},
        ]
        leads, errors = discovery.discover(lambda _: results, registry, queries=["test"])
        self.assertFalse(errors)
        self.assertEqual([lead["domain"] for lead in leads], ["good.example.org"])
        self.assertFalse(leads[0]["submission_sent"])
        self.assertFalse(leads[0]["quality_verified"])

    def test_requires_review_before_any_outreach(self):
        lead = discovery.assess({
            "link": "https://editorial.example.com/resources",
            "title": "Suggest a resource",
            "snippet": "Curated website directory submission"
        }, set())
        self.assertEqual(lead["status"], "manual_policy_review")
        self.assertTrue(lead["lead_score"] > 0)


if __name__ == "__main__":
    unittest.main()
