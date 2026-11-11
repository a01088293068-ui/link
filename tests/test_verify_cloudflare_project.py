import unittest
from seo.verify_cloudflare_project import verify_project


class TargetGuardTests(unittest.TestCase):
    def test_exact_project_and_custom_domain(self):
        self.assertTrue(verify_project({"success":True,"result":{
            "name":"my-pages","production_branch":"main",
            "domains":["my-pages.pages.dev","linkwiki.info"]}},"my-pages"))

    def test_other_project_or_other_domain_never_deployed(self):
        good={"success":True,"result":{"name":"my-pages",
            "production_branch":"main","domains":["linkwiki.info"]}}
        for candidate, name in [
            ({"success":False,"result":good["result"]}, "my-pages"),
            (good, "other-project"),
            ({"success":True,"result":dict(good["result"], domains=["other.info"])}, "my-pages"),
            ({"success":True,"result":dict(good["result"], production_branch="develop")}, "my-pages"),
        ]:
            with self.assertRaises(ValueError):
                verify_project(candidate,name)


if __name__ == "__main__":
    unittest.main()
