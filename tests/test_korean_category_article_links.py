"""Ensure Korean public-service guides have crawlable relevant category entry points."""
import importlib.util
from pathlib import Path
import unittest

from seo.auto_seo import related_categories

ROOT = Path(__file__).resolve().parents[1]
NEW_ARTICLES = (
    "seo-20261110-korean-public-services-guide.md",
    "seo-20261110-korean-business-portals-guide.md",
)


class KoreanCategoryArticleLinksTests(unittest.TestCase):
    def test_related_categories_for_real_published_guides(self):
        for name in NEW_ARTICLES:
            title = next(line[2:].strip() for line in
                         (ROOT / "content" / name).read_text(encoding="utf-8").splitlines()
                         if line.startswith("# "))
            with self.subTest(name=name):
                self.assertIn("/categories/search",
                              [path for _, path in related_categories(title)])

    def test_build_links_to_real_articles_from_category_page(self):
        # Build's category-article selector chooses from titles in real posts.
        spec = importlib.util.spec_from_file_location("linkwiki_build", ROOT / "build.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        posts = []
        for name in NEW_ARTICLES:
            title = next(line[2:].strip() for line in
                         (ROOT / "content" / name).read_text(encoding="utf-8").splitlines()
                         if line.startswith("# "))
            posts.append({"title": title, "url": "/blog/" + Path(name).stem + "/"})
        selected = builder.category_article_links(posts, "search")
        self.assertEqual({p["url"] for p in selected}, {p["url"] for p in posts})


if __name__ == "__main__":
    unittest.main()
