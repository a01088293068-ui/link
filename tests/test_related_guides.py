import unittest

from build import add_editorial_related_articles


class RelatedGuidesTests(unittest.TestCase):
    def test_only_matching_categories_are_crosslinked(self):
        posts = [
            {"title": "국내 커뮤니티 사이트모음", "url": "/blog/community-a/"},
            {"title": "게임 커뮤니티 링크모음", "url": "/blog/community-b/"},
            {"title": "AI 도구 사이트모음", "url": "/blog/ai-tools/"},
        ]
        sections = add_editorial_related_articles(posts)
        self.assertIn("/blog/community-a/", sections)
        self.assertIn('href="/blog/community-b/"', sections["/blog/community-a/"])
        self.assertNotIn('href="/blog/ai-tools/"', sections["/blog/community-a/"])
        self.assertNotIn("/blog/ai-tools/", sections)

    def test_never_self_link_and_limit_matches(self):
        posts = [
            {"title": "국내 커뮤니티 사이트모음", "url": f"/blog/community-{i}/"}
            for i in range(7)
        ]
        sections = add_editorial_related_articles(posts, max_links=2)
        self.assertEqual(len(sections), 7)
        for item in posts:
            self.assertNotIn(f'href="{item["url"]}"', sections[item["url"]])
            self.assertEqual(sections[item["url"]].count("<li>"), 2)

    def test_unknown_topics_do_not_force_irrelevant_links(self):
        posts = [
            {"title": "독립적인 실험 주제 XYZ", "url": "/blog/xyz/"},
            {"title": "국내 커뮤니티 사이트모음", "url": "/blog/community/"},
        ]
        self.assertEqual(add_editorial_related_articles(posts), {})

    def test_invalid_limit_rejected(self):
        with self.assertRaises(ValueError):
            add_editorial_related_articles([], 0)


if __name__ == "__main__":
    unittest.main()
