"""Release-integrity checks: generated directory must stay crawlable."""
import unittest
from pathlib import Path
from seo.directory_release_gate import validate, CATEGORIES, ORIGIN

def fixture(card_count=13):
    labels = {
        "community":"커뮤니티", "korean":"한인교민", "comics-directory":"만화",
        "webtoon":"만화·웹툰", "ai":"AI 도구", "search":"검색·포털",
        "sports":"스포츠", "video":"영상·OTT", "finance":"금융·경제",
        "education":"교육·취업", "news":"뉴스·언론", "shopping":"쇼핑·가격비교",
        "travel":"생활·교통·여행",
    }
    source = [{"name": f"Example {slug}", "category": label}
              for slug, label in labels.items()]
    cards = ''.join('<article class="v6-card" id="site-'+format(i,'014x')+'"><h3>Example</h3>'
                    '<a href="https://example.org/">사이트 방문</a></article>'
                    for i in range(card_count))
    nav = ''.join(f'<a href="/categories/{slug}">category</a>' for slug in CATEGORIES)
    directory = ('<html><head><link rel="canonical" href="'+ORIGIN+'/directory">'
                 '</head><body><h1>' + str(card_count) + '개 사이트 주소 검색: 이름·도메인·분야별 목록</h1>'
                 f'<p>{card_count}개 등록 사이트</p><section>주소모음 링크모음 사이트모음</section><nav>{nav}</nav>'
                 '<form id="v6-form"></form>'
                 f'<div id="v6-results">{cards}</div>'
                 '<section id="directory-quick-compare"><ul>' + nav
                 + '<a href="#site-00000000000000">첫 번째 항목</a>'
                 + '</ul></section></body></html>')
    home = ('<html><head><title>주소모음 검색</title>'
            '<link rel="canonical" href="'+ORIGIN+'/"></head><body>'
            '<a href="/directory">directory</a><a href="/categories/">분야</a>'
            + nav + '</body></html>')
    category = {}
    for slug in CATEGORIES:
        listing = ('<article class="item"><strong>Example '+slug+'</strong>'
                   '<a href="https://example.org/">사이트 방문</a></article>')
        category[slug] = ('<html><head><link rel="canonical" href="'+ORIGIN+
                          '/categories/'+slug+'"></head><body>'
                          '<a href="/directory">전체 목록</a><a href="/categories/">분야</a>'
                          + listing + '</body></html>')
    sitemap = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + ''.join('<url><loc>'+ORIGIN+path+'</loc></url>'
                         for path in ('/','/directory','/categories/')
                         + tuple('/categories/' + slug for slug in CATEGORIES))
               + '</urlset>')
    return directory, home, source, category, sitemap

class DirectoryReleaseGateTests(unittest.TestCase):
    def test_complete_static_directory_passes(self):
        self.assertEqual(validate(*fixture()), [])

    def test_missing_quick_category_navigation_fails(self):
        parts = list(fixture())
        parts[0] = parts[0].replace('id="directory-quick-compare"', 'id="removed"')
        self.assertTrue(any("quick category comparison" in issue for issue in validate(*parts)))

    def test_broken_example_anchor_stops_release(self):
        parts = list(fixture())
        parts[0] = parts[0].replace('href="#site-00000000000000"',
                                    'href="#site-aaaaaaaaaaaaaa"')
        self.assertIn("quick comparison has missing or broken listing anchors",
                      validate(*parts))

    def test_missing_static_card_fails_even_if_js_would_fill_it(self):
        parts = list(fixture())
        parts[0] = parts[0].replace('class="v6-card"', 'class="removed"',1)
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

    def test_homepage_must_link_to_every_category_and_category_hub(self):
        parts = list(fixture())
        parts[1] = parts[1].replace(
            '<a href="/categories/search">category</a>', ''
        ).replace('<a href="/categories/">분야</a>', '')
        issues = validate(*parts)
        self.assertIn("homepage lacks crawlable category hub link", issues)
        self.assertIn("homepage lacks crawlable category link: search", issues)

    def test_empty_category_listing_fails_even_when_directory_is_complete(self):
        parts = list(fixture())
        parts[3]["finance"] = parts[3]["finance"].replace(
            '<article class="item"><strong>Example finance</strong>'
            '<a href="https://example.org/">사이트 방문</a></article>', ''
        )
        self.assertIn(
            "static category cards finance: 0 != data 1",
            validate(*parts),
        )

    def test_category_noindex_or_missing_internal_path_fails(self):
        parts = list(fixture())
        parts[3]["shopping"] = parts[3]["shopping"].replace(
            '</head>', '<meta name="robots" content="noindex"></head>'
        ).replace('<a href="/directory">전체 목록</a>', '')
        issues = validate(*parts)
        self.assertIn("category has noindex: shopping", issues)
        self.assertIn("category lacks crawlable directory navigation: shopping", issues)

    def test_sitemap_requires_every_canonical_category_url(self):
        parts = list(fixture())
        parts[4] = parts[4].replace(
            '<url><loc>'+ORIGIN+'/categories/finance</loc></url>', ''
        )
        self.assertIn(
            'sitemap missing category: '+ORIGIN+'/categories/finance',
            validate(*parts),
        )

    def test_sitemap_requires_canonical_directory(self):
        parts = list(fixture())
        parts[4] = parts[4].replace('<loc>'+ORIGIN+'/directory</loc>',
                                  '<loc>'+ORIGIN+'/directory.html</loc>')
        self.assertIn('sitemap missing: '+ORIGIN+'/directory', validate(*parts))

if __name__ == "__main__":
    unittest.main()
