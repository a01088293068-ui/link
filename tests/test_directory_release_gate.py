"""Release-integrity checks: generated directory must stay crawlable."""
import unittest
from pathlib import Path
from seo.directory_release_gate import validate, CATEGORIES, ORIGIN

def fixture(card_count=2):
    source = [{"name": f"Example {i}", "category":"검색·포털"} for i in range(card_count)]
    cards = ''.join('<article class="v6-card"><h3>Example</h3>'
                    '<a href="https://example.org/">사이트 방문</a></article>'
                    for _ in range(card_count))
    nav = ''.join(f'<a href="/categories/{slug}">category</a>' for slug in CATEGORIES)
    directory = ('<html><head><link rel="canonical" href="'+ORIGIN+'/directory">'
                 '</head><body><h1>주소모음·링크모음·사이트모음</h1>'
                 f'<p>{card_count}개 등록 사이트</p><nav>{nav}</nav>'
                 f'<div id="v6-results">{cards}</div></body></html>')
    home = ('<html><head><title>주소모음·링크모음·사이트모음</title>'
            '<link rel="canonical" href="'+ORIGIN+'/"></head><body>'
            '<a href="/directory">directory</a></body></html>')
    category = {slug: ('<html><head><link rel="canonical" href="'+ORIGIN+
                       '/categories/'+slug+'"></head><body></body></html>')
                for slug in CATEGORIES}
    sitemap = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + ''.join('<url><loc>'+ORIGIN+path+'</loc></url>'
                         for path in ('/','/directory','/categories/'))
               + '</urlset>')
    return directory, home, source, category, sitemap

class DirectoryReleaseGateTests(unittest.TestCase):
    def test_complete_static_directory_passes(self):
        self.assertEqual(validate(*fixture()), [])

    def test_missing_static_card_fails_even_if_js_would_fill_it(self):
        parts = list(fixture())
        parts[0] = parts[0].replace('<article class="v6-card">','<article class="removed">',1)
        self.assertTrue(any('static directory cards' in x for x in validate(*parts)))

    def test_missing_category_or_canonical_fails(self):
        parts = list(fixture())
        parts[3].pop('ai')
        parts[0] = parts[0].replace('href="https://linkwiki.info/directory"',
                                    'href="https://linkwiki.info/directory.html"')
        issues = validate(*parts)
        self.assertTrue(any('canonical' in x for x in issues))
        self.assertIn('missing category file: ai', issues)

    def test_noindex_and_missing_home_link_fail(self):
        parts = list(fixture())
        parts[0] = parts[0].replace('</head>','<meta name="robots" content="noindex"></head>')
        parts[1] = parts[1].replace('href="/directory"', 'href="/directory.html"')
        issues = validate(*parts)
        self.assertIn('directory has noindex', issues)
        self.assertIn('homepage lacks crawlable canonical /directory link', issues)

    def test_sitemap_requires_canonical_directory(self):
        parts = list(fixture())
        parts[4] = parts[4].replace('<loc>'+ORIGIN+'/directory</loc>',
                                  '<loc>'+ORIGIN+'/directory.html</loc>')
        self.assertIn('sitemap missing: '+ORIGIN+'/directory', validate(*parts))

if __name__ == "__main__":
    unittest.main()
