from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from build import add_breadcrumb_data, normalize_page_links, stable_post_lastmod, category_article_links
import json
import re
from seo import auto_seo

PUBLISHED_COUNT = len(json.loads((Path(__file__).resolve().parents[1] / 'assets/verified-directory.json').read_text(encoding='utf-8')))


class SEOReleaseRegressionTests(unittest.TestCase):
    def test_directory_guide_links_are_published_and_task_relevant(self):
        from build import directory_relevant_guides
        from seo.site_audit import internal_inbound_links
        root = Path(__file__).resolve().parents[1]
        page = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertEqual(page.count('id="site-related-guides"'), 1)
        self.assertIn('href="#site-related-guides"', page)
        section = re.search(
            r'<section id="site-related-guides".*?</section>', page, re.S).group()
        self.assertIn("사이트를 어떻게 검색하나요?", section)
        self.assertIn("사이트모음은 어떤 기준으로 비교하나요?", section)
        self.assertIn("광고 링크는 어떻게 구분하나요?", section)
        urls = re.findall(r'href="(/blog/[^"]+/)"', section)
        self.assertEqual(len(urls), 3)
        self.assertEqual(len(set(urls)), 3)
        inbound = internal_inbound_links(root / "dist")
        for url in urls:
            self.assertTrue((root / "dist" / url.lstrip("/") / "index.html").is_file())
            self.assertIn("/directory", inbound[url])
        with self.assertRaisesRegex(RuntimeError, "two distinct"):
            directory_relevant_guides([])

    def test_directory_purpose_chooser_is_genuinely_cross_category(self):
        from build import directory_purpose_comparison, DIRECTORY_PURPOSE_COMPARISONS, CATEGORY_LANDING
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        html = directory_purpose_comparison(records, CATEGORY_LANDING)
        output = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertIn(html, output)
        self.assertEqual(html.count('class="seo-purpose-pair"'), 4)
        self.assertIn('href="#site-purpose-comparison"', output)
        self.assertLess(output.index('href="#site-purpose-comparison"'),
                        output.index('id="site-purpose-comparison"'))
        for title, (left, _), (right, _), advice in DIRECTORY_PURPOSE_COMPARISONS:
            self.assertIn(title, html)
            self.assertIn(advice, html)
            self.assertIn(f'href="/categories/{left}"', html)
            self.assertIn(f'href="/categories/{right}"', html)
            for slug in (left, right):
                category = next(cat for cat, code, _, _ in CATEGORY_LANDING if code == slug)
                name = next(row["name"] for row in records if row["category"] == category)
                self.assertIn(name, html)
        self.assertNotIn("추천 1위", html)

    def test_category_editorial_guides_are_unique_and_grounded(self):
        from build import category_decision_guide, CATEGORY_DECISION_GUIDES, CATEGORY_LANDING
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        self.assertEqual(len(CATEGORY_DECISION_GUIDES), 8)
        seen_headings = set()
        for category, slug, _, _ in CATEGORY_LANDING:
            html = category_decision_guide(slug, records)
            page = (root / "dist/categories" / (slug + ".html")).read_text(encoding="utf-8")
            self.assertIn(html, page, slug)
            self.assertEqual(html.count("<li><h3>"), 3, slug)
            self.assertEqual(page.count('aria-label="이 분야의 목적별 선택 방법"'), 1, slug)
            self.assertIn('href="/guides/address-check"', html)
            names = [x["name"] for x in records if x["category"] == category]
            self.assertIn(names[0], html)
            self.assertIn(names[1], html)
            headings = re.findall(r"<li><h3>(.*?)</h3>", html)
            self.assertTrue(seen_headings.isdisjoint(headings), slug)
            seen_headings.update(headings)
        with self.assertRaisesRegex(RuntimeError, "missing"):
            category_decision_guide("nonexistent", records)

    def test_korean_business_official_address_guide_is_published_and_discoverable(self):
        root = Path(__file__).resolve().parents[1]
        slug = "seo-20261110-korean-business-portals-guide"
        source = root / "content" / (slug + ".md")
        original = source.read_text(encoding="utf-8")
        for name in (
            "K-Startup 창업지원포털", "기업마당", "KIPRIS 지식재산정보검색",
            "특허로", "관세청 유니패스", "대한상공회의소 코참넷",
        ):
            self.assertIn(name, original)
        self.assertGreater(len(original), 1800)
        rendered = (root / "dist/blog" / slug / "index.html").read_text(encoding="utf-8")
        url = "https://linkwiki.info/blog/" + slug + "/"
        self.assertIn('href="' + url + '" rel="canonical"', rendered)
        self.assertIn("창업지원사업", rendered)
        self.assertIn("/categories/search", rendered)
        index = (root / "dist/blog/index.html").read_text(encoding="utf-8")
        self.assertIn('/blog/' + slug + '/', index)
        sitemap = (root / "dist/sitemap.xml").read_text(encoding="utf-8")
        self.assertIn('<loc>' + url + '</loc>', sitemap)

    def test_search_category_metadata_covers_real_korean_public_services(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "categories/search.html").read_text(encoding="utf-8")
        built = (root / "dist/categories/search.html").read_text(encoding="utf-8")
        for html in (source, built):
            self.assertIn("검색·포털·공공정보 사이트모음", html)
            self.assertIn("국민신문고·위택스·국민건강보험공단", html)
            self.assertIn("민원·복지·건강보험·연금·학술정보 사이트", html)
            self.assertIn("국내 공공서비스를 목적별로 찾는 방법", html)
            self.assertIn("창업·특허·기업지원 사이트는 이렇게 구분하세요", html)
            self.assertIn("K-Startup 창업지원포털은 창업 단계별 지원사업", html)
            self.assertIn("국민신문고는 기관에 민원", html)
            self.assertIn("식품안전나라는 식품 회수", html)
            self.assertEqual(html.count('<article class="item"'), 50)
            self.assertNotIn('name="robots" content="noindex"', html)
        self.assertIn('href="https://linkwiki.info/categories/search"', built)

    def test_korean_search_guide_reflects_actual_official_directory_entries(self):
        from build import category_decision_guide
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        actual_names = {row["name"] for row in records}
        names = ("정부24", "복지로", "한국장학재단",
                 "학술연구정보서비스 RISS", "국가통계포털 KOSIS", "국가법령정보센터",
                 "국민신문고", "위택스", "국립중앙도서관", "국가전자도서관",
                 "표준국어대사전", "K-Startup 창업지원포털", "기업마당",
                 "KIPRIS 지식재산정보검색", "특허로", "관세청 유니패스",
                 "대한상공회의소 코참넷")
        self.assertTrue(set(names).issubset(actual_names))
        html = category_decision_guide("search", records)
        built = (root / "dist/categories/search.html").read_text(encoding="utf-8")
        for name in names:
            self.assertIn(name, html)
            self.assertIn(name, built)
        self.assertIn("학술자료", html)
        self.assertIn("민원 신청", html)

    def test_all_eight_categories_offer_two_contextual_crawlable_paths(self):
        from build import related_category_navigation, RELATED_CATEGORY_PATHS, CATEGORY_LANDING
        from seo.site_audit import internal_inbound_links
        root = Path(__file__).resolve().parents[1]
        dist = root / "dist"
        self.assertEqual(len(RELATED_CATEGORY_PATHS), len(CATEGORY_LANDING))
        inbound = internal_inbound_links(dist)
        for _, slug, _, _ in CATEGORY_LANDING:
            block = related_category_navigation(slug)
            page = (dist / "categories" / (slug + ".html")).read_text(encoding="utf-8")
            self.assertIn(block, page)
            self.assertEqual(block.count("<li>"), 2)
            self.assertNotIn(f'href="/categories/{slug}"', block)
            for target, _ in RELATED_CATEGORY_PATHS[slug]:
                url = f"/categories/{target}"
                self.assertIn(f'href="{url}"', block)
                self.assertIn("/categories/" + slug, inbound[url])
        with self.assertRaises(RuntimeError):
            related_category_navigation("unlisted")

    def test_sitemap_lastmod_tracks_real_core_page_changes_only(self):
        from build import apply_significant_lastmods, SITE
        import xml.etree.ElementTree as ET
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        root = ET.Element(f"{{{ns}}}urlset")
        for path in ("/", "/directory", "/categories/", "/guides/security"):
            item = ET.SubElement(root, f"{{{ns}}}url")
            ET.SubElement(item, f"{{{ns}}}loc").text = SITE + path
            if path == "/":
                ET.SubElement(item, f"{{{ns}}}lastmod").text = "2026-10-29"
        updates = {"/": "2026-11-07", "/directory": "2026-11-07",
                   "/categories/": "2026-11-07"}
        apply_significant_lastmods(root, updates, ns)
        values = {el.find(f"{{{ns}}}loc").text:
                  el.find(f"{{{ns}}}lastmod").text if el.find(f"{{{ns}}}lastmod") is not None else None
                  for el in root.findall(f"{{{ns}}}url")}
        self.assertEqual(values[SITE + "/directory"], "2026-11-07")
        self.assertEqual(values[SITE + "/"], "2026-11-07")
        self.assertEqual(values[SITE + "/categories/"], "2026-11-07")
        self.assertIsNone(values[SITE + "/guides/security"])
        apply_significant_lastmods(root, updates, ns)
        self.assertEqual(len(root.findall(f".//{{{ns}}}lastmod")), 3)
        with self.assertRaisesRegex(RuntimeError, "absent from sitemap"):
            apply_significant_lastmods(root, {"/unknown": "2026-11-07"}, ns)
        with self.assertRaisesRegex(RuntimeError, "Invalid calendar"):
            apply_significant_lastmods(root, {"/": "2026-11-31"}, ns)

    def test_generated_sitemap_has_verified_significant_dates(self):
        import xml.etree.ElementTree as ET
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "seo/significant-page-updates.json").read_text(encoding="utf-8"))
        tree = ET.parse(root / "dist/sitemap.xml")
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        values = {
            item.find(ns + "loc").text: item.find(ns + "lastmod").text
            if item.find(ns + "lastmod") is not None else None
            for item in tree.getroot().findall(ns + "url")
        }
        for path, value in data.items():
            self.assertEqual(values["https://linkwiki.info" + path], value)

    def test_build_help_uses_registered_counts_and_real_navigation(self):
        from build import directory_search_help, CATEGORY_LANDING
        import json
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        section = directory_search_help(records, CATEGORY_LANDING)
        self.assertIn(f"{len(records)}개 사이트", section)
        self.assertIn('href="/guides/address-check"', section)
        self.assertIn('href="/guides/link-troubleshooting"', section)
        self.assertNotIn("FAQPage", section)
        self.assertEqual(section.count("<h4>"), 3)
        with self.assertRaises(RuntimeError):
            directory_search_help([], CATEGORY_LANDING)
        generated = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertEqual(generated.count('class="lw-safety-note seo-search-help"'), 1)
        self.assertEqual(generated.count("주소모음·링크모음 검색 사용 방법"), 1)

    def test_canonical_directory_has_local_only_address_verifier(self):
        from build import directory_address_inspector
        root = Path(__file__).resolve().parents[1]
        generated = (root / "dist/directory.html").read_text(encoding="utf-8")
        section = directory_address_inspector()
        self.assertIn('id="lw-address-form"', section)
        self.assertIn('id="lw-address-result"', section)
        self.assertIn("외부 사이트에도 접속하지 않습니다", section)
        self.assertEqual(generated.count('id="address-inspector"'), 1)
        self.assertEqual(generated.count('id="lw-address-form"'), 1)
        self.assertEqual(generated.count('/assets/address-inspector.js'), 1)
        self.assertEqual(generated.count('class="v6-card"'), PUBLISHED_COUNT)
        self.assertIn('href="https://linkwiki.info/directory"', generated)
        self.assertNotIn('name="robots" content="noindex"', generated)

    def test_korean_first_shortcuts_exist_on_both_canonical_landings(self):
        from build import korean_first_shortcuts, KOREAN_FIRST_SEARCH_NAMES
        from urllib.parse import parse_qs, urlsplit
        import json
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        generated = korean_first_shortcuts(records)
        self.assertEqual(generated.count('class="lw-safety-note korean-first-shortcuts"'), 1)
        self.assertEqual(generated.count('href="/directory?q='), len(KOREAN_FIRST_SEARCH_NAMES))
        for new_name in ("학술연구정보서비스 RISS", "복지로", "한국장학재단"):
            self.assertIn(new_name, KOREAN_FIRST_SEARCH_NAMES)
            self.assertIn(">" + new_name + "</a>", generated)
        for page in ("index.html", "directory.html"):
            content = (root / "dist" / page).read_text(encoding="utf-8")
            self.assertEqual(content.count('class="lw-safety-note korean-first-shortcuts"'), 1)
            self.assertIn('국내 사이트 먼저 찾기', content)
            for name in KOREAN_FIRST_SEARCH_NAMES:
                self.assertIn('>' + name + '</a>', content)
        directory = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertLess(directory.index('class="lw-safety-note korean-first-shortcuts"'),
                        directory.index('id="v6-form"'))
        self.assertEqual(directory.count('class="v6-card"'), len(records))

    def test_directory_search_examples_link_to_real_registered_names(self):
        from build import directory_search_help, CATEGORY_LANDING
        from urllib.parse import parse_qs, urlsplit
        root = Path(__file__).resolve().parents[1]
        entries = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        html = directory_search_help(entries, CATEGORY_LANDING)
        section = re.search(r'<div class="lw-search-examples">.*?</div>', html, re.S)
        self.assertIsNotNone(section)
        hrefs = re.findall(r'<a href="([^"]+)"', section.group())
        self.assertEqual(len(hrefs), 5)
        actual_names = {item["name"] for item in entries}
        actual_hosts = {urlsplit(item["url"]).hostname for item in entries}
        observed_names, observed_hosts = set(), set()
        for href in hrefs:
            parts = urlsplit(href)
            self.assertEqual(parts.path, "/directory")
            query = parse_qs(parts.query)["q"][0]
            self.assertTrue(query in actual_names or query in actual_hosts)
            if query in actual_names:
                observed_names.add(query)
            if query in actual_hosts:
                observed_hosts.add(query)
        self.assertEqual(len(observed_names), 3)
        self.assertEqual(len(observed_hosts), 2)
        generated = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertIn("실제 등록 사이트 검색 예시", generated)
        self.assertIn('class="lw-search-examples"', generated)
        self.assertEqual(generated.count('class="lw-search-examples"'), 1)

    def test_directory_guide_and_comparison_are_reachable_from_top_navigation(self):
        root = Path(__file__).resolve().parents[1]
        page = (root / "dist/directory.html").read_text(encoding="utf-8")
        for anchor in ("site-list-guide", "site-category-comparison", "site-purpose-comparison", "site-related-guides"):
            self.assertEqual(page.count(f'id="{anchor}"'), 1)
            self.assertIn(f'href="#{anchor}"', page)
            self.assertLess(page.index(f'href="#{anchor}"'), page.index(f'id="{anchor}"'))

    def test_hub_examples_do_not_truncate_community_or_korean_names(self):
        root = Path(__file__).resolve().parents[1]
        page = (root / "dist/categories/index.html").read_text(encoding="utf-8")
        import json
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        for category in ("커뮤니티", "한인교민"):
            first = [entry["name"] for entry in records if entry["category"] == category][:3]
            self.assertIn("등록 예시: " + ", ".join(first), page)
        self.assertNotIn("등록 예시: ", page.split("등록 예시: ", 1)[0])

    def test_category_hub_shows_factual_registered_site_examples(self):
        root = Path(__file__).resolve().parents[1]
        generated = (root / "dist/categories/index.html").read_text(encoding="utf-8")
        self.assertIn("등록 예시: ", generated)
        self.assertIn("ChatGPT", generated)
        self.assertIn("네이버 스포츠", generated)

    def test_directory_examples_display_real_domains_without_implying_verification(self):
        root = Path(__file__).resolve().parents[1]
        generated = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertIn("등록 도메인: ", generated)
        self.assertIn("서비스의 공식 인증·현재 접속 상태", generated)

    def test_home_search_submits_to_canonical_directory_without_html_redirect(self):
        from build import polish_home_intent
        root = Path(__file__).resolve().parents[1]
        source = (root / "index.html").read_text(encoding="utf-8")
        home = (root / "dist/index.html").read_text(encoding="utf-8")
        form = '<form action="/directory" class="lw-search" method="get" role="search">'
        self.assertEqual(home.count(form), 1)
        self.assertNotIn('<form action="directory.html"', home)
        self.assertIn('name="q"', home)
        self.assertEqual(polish_home_intent(source).count(form), 1)
        # The canonical search action must survive further build passes.
        self.assertEqual(polish_home_intent(polish_home_intent(source)).count(form), 1)

    def test_primary_directory_metadata_and_dynamic_heading_match_three_intents(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "dist/directory.html").read_text(encoding="utf-8")
        script = (root / "dist/assets/directory.js").read_text(encoding="utf-8")
        title = f"사이트모음 전체 목록: {PUBLISHED_COUNT}개 사이트 검색 | 링크위키"
        heading = "주소모음·링크모음·사이트모음 통합 검색"
        self.assertIn("<title>" + title + "</title>", html)
        self.assertIn(f"전체 사이트모음에서 {PUBLISHED_COUNT}개 사이트", html)
        self.assertIn('property="og:title"', html)
        self.assertIn('name="twitter:title"', html)
        self.assertIn('<h1 id="directory-heading">' + heading + "</h1>", html)
        self.assertIn("?'"+heading+"'", script)
        self.assertIn('href="https://linkwiki.info/directory"', html)
        self.assertIn('name="robots"', html)
        self.assertIn('id="v6-form"', html)
        self.assertIn('id="v6-results"', html)
        self.assertEqual(html.count('<h1'), 1)
        for keyword in ("주소모음", "링크모음", "사이트모음"):
            self.assertIn(keyword, html)
        self.assertNotIn("분야별 사이트모음·주소모음 검색", script)

    def test_homepage_and_directory_have_distinct_search_intent_titles(self):
        root = Path(__file__).resolve().parents[1] / "dist"
        home = (root / "index.html").read_text(encoding="utf-8")
        directory = (root / "directory.html").read_text(encoding="utf-8")
        import re
        get_title = lambda html: re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        home_title = get_title(home)
        directory_title = get_title(directory)
        self.assertNotEqual(home_title, directory_title)
        self.assertIn(f"{PUBLISHED_COUNT}개 사이트", directory_title)
        self.assertIn("전체 목록", directory_title)
        self.assertIn(f"{PUBLISHED_COUNT}개 사이트", home_title)
        # The directory remains the indexable target, never the legacy .html URL.
        self.assertIn('href="https://linkwiki.info/directory"', directory)
        self.assertNotIn('href="https://linkwiki.info/directory.html" rel="canonical"', directory)

    def test_directory_count_rewrites_korean_object_particle_and_preserves_category_count(self):
        from build import sync_directory_count
        sample = ('<title>97개 사이트 목록</title><meta content="97개 사이트를 비교" />'
                  '<meta property="og:title" content="97개 사이트" />'
                  '<p>97개 등록 사이트의 설명</p><p>97개 사이트 검색</p>'
                  '<p>등록 사이트 97개</p><p>8개 분야</p>')
        changed = sync_directory_count(sample, 98)
        self.assertIn("98개 사이트를 비교", changed)
        self.assertIn("98개 등록 사이트의 설명", changed)
        self.assertIn("등록 사이트 98개", changed)
        self.assertIn("8개 분야", changed)

    def test_directory_schema_reflects_only_real_category_pages(self):
        from build import directory_collection_schema, CATEGORY_LANDING
        examples = [
            {"name": "예시 검색", "category": "검색·포털"},
            {"name": "예시 커뮤니티", "category": "커뮤니티"},
        ]
        output = directory_collection_schema(examples, CATEGORY_LANDING)
        schema = json.loads(re.search(r'<script[^>]*>(.*?)</script>', output).group(1))
        self.assertEqual(schema["@type"], "CollectionPage")
        self.assertEqual(schema["url"], "https://linkwiki.info/directory")
        items = schema["mainEntity"]["itemListElement"]
        self.assertEqual(schema["mainEntity"]["numberOfItems"], 2)
        self.assertEqual([item["position"] for item in items], [1, 2])
        self.assertEqual({item["url"] for item in items}, {
            "https://linkwiki.info/categories/community",
            "https://linkwiki.info/categories/search",
        })
        self.assertNotIn("aggregateRating", output)
        with self.assertRaises(RuntimeError):
            directory_collection_schema([], CATEGORY_LANDING)

    def test_built_directory_structured_data_matches_published_categories(self):
        from build import CATEGORY_LANDING
        root = Path(__file__).resolve().parents[1]
        html = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="directory-category-schema"'), 1)
        match = re.search(
            r'<script id="directory-category-schema" type="application/ld\+json">(.*?)</script>',
            html, re.S)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        urls = {row["url"] for row in data["mainEntity"]["itemListElement"]}
        self.assertEqual(urls, {"https://linkwiki.info/categories/" + slug
                                for _, slug, _, _ in CATEGORY_LANDING})
        self.assertEqual(data["mainEntity"]["numberOfItems"], len(CATEGORY_LANDING))
        self.assertNotIn("ratingValue", match.group(1))

    def test_primary_keyword_queries_and_multiword_search_are_wired(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "dist/assets/directory.js").read_text(encoding="utf-8")
        search = (root / "dist/assets/directory-search.js").read_text(encoding="utf-8")
        page = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertIn("['주소모음','링크모음','사이트모음']", script)
        self.assertIn("window.LinkWikiSearch.sortResults", script)
        self.assertIn("terms.every(term => haystack.includes(term))", search)
        self.assertIn("const CORE = new Set", search)
        self.assertIn("assets/directory-search.js?v=20261107-relevance", page)
        self.assertIn("assets/directory.js?v=20261107-relevance", page)
        self.assertLess(page.index('assets/directory-search.js'), page.index('assets/directory.js'))
        self.assertIn('id="v6-empty"', page)
        self.assertIn('id="v6-results"', page)

    def test_latest_published_article_is_in_built_sitemap_with_matching_canonical(self):
        root = Path(__file__).resolve().parents[1]
        posts = sorted((root / "content").glob("seo-*.md"))
        self.assertTrue(posts, "No published SEO article available for smoke test")
        slug = posts[-1].stem
        public_path = f"/blog/{slug}/"
        url = "https://linkwiki.info" + public_path
        output = root / "dist"
        sitemap = (output / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"<loc>{url}</loc>", sitemap)
        html_path = output / "blog" / slug / "index.html"
        self.assertTrue(html_path.is_file(), f"Missing published article: {html_path}")
        html = html_path.read_text(encoding="utf-8")
        self.assertIn(f'href="{url}"', html)
        self.assertIn('name="robots" content="index,follow"', html)
        self.assertNotIn('name="robots" content="noindex', html)

    def test_guide_article_links_to_primary_directory_and_relevant_categories(self):
        from build import article_category_links
        root = Path(__file__).resolve().parents[1]
        guides = sorted((root / "dist/blog").glob("seo-*/index.html"))
        self.assertGreater(len(guides), 0)
        for file in guides:
            html = file.read_text(encoding="utf-8")
            self.assertIn('<a href="/directory">전체 주소모음·사이트모음 검색</a>', html)
            self.assertIn('<a href="/categories/">분야별 링크모음 보기</a>', html)
            self.assertEqual(html.count('<a href="/directory">전체 주소모음·사이트모음 검색</a>'), 1)
        links = article_category_links("AI 글쓰기", [
            ("AI 도구", "/categories/ai"),
            ("없는 분야", "/categories/nonexistent"),
            ("AI 도구", "/categories/ai"),
            ("검색·포털", "/categories/search"),
        ])
        self.assertEqual(links.count('href="/categories/ai"'), 1)
        self.assertIn('href="/categories/search"', links)
        self.assertNotIn("nonexistent", links)
        self.assertEqual(article_category_links("일반 안내", []), "")

    def test_category_article_links_only_relevant_published_guides(self):
        posts = [
            {"title": "검색 포털 링크모음 목적별 비교", "url": "/blog/search-example/"},
            {"title": "사이트모음 비교 기준", "url": "/blog/general-example/"},
            {"title": "스포츠 경기 일정 사이트 비교", "url": "/blog/sports-example/"},
        ]
        self.assertEqual(category_article_links(posts, "search"),
                         [posts[0]])
        self.assertEqual(category_article_links(posts, "sports"),
                         [posts[2]])
        self.assertEqual(category_article_links(posts, "ai"), [])

    def test_category_page_links_to_actual_search_post_after_build(self):
        root = Path(__file__).resolve().parents[1]
        output = root / "dist" / "categories" / "search.html"
        self.assertTrue(output.is_file(), "Generated search category page missing")
        html = output.read_text(encoding="utf-8")
        self.assertIn('이 분야의 이용 가이드', html)
        self.assertIn('/blog/seo-20261030-26325b73af/', html)

    def test_directory_landing_has_all_eight_crawlable_categories_with_counts(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        counts = {}
        for record in records:
            counts[record["category"]] = counts.get(record["category"], 0) + 1
        html = (root / "dist/directory.html").read_text(encoding="utf-8")
        nav = re.search(r'<nav aria-label="분야별 사이트모음 바로가기".*?</nav>',
                        html, re.S)
        self.assertIsNotNone(nav)
        from build import CATEGORY_LANDING
        for category, slug, _, _ in CATEGORY_LANDING:
            self.assertIn(f'href="/categories/{slug}"', nav.group())
            self.assertIn(f'{category} {counts[category]}개', nav.group())
        self.assertEqual(nav.group().count('href="/categories/'), len(CATEGORY_LANDING) + 1)

    def test_directory_category_overview_is_grounded_in_registered_sites(self):
        from build import CATEGORY_LANDING, directory_category_overview
        records = [
            {"name": "예시 검색", "category": "검색·포털", "url": "https://example.com", "description": "웹 검색에 이용하는 예시입니다."},
            {"name": "예시 커뮤니티", "category": "커뮤니티", "url": "https://example.org", "description": "커뮤니티 게시판 예시입니다."},
            {"name": "<script>위험</script>", "category": "커뮤니티", "url": "https://example.net", "description": "다른 게시판 예시입니다."},
        ]
        result = directory_category_overview(records, CATEGORY_LANDING)
        self.assertIn("예시 검색", result)
        self.assertIn("예시 커뮤니티", result)
        self.assertIn("등록 사이트 2개", result)
        self.assertIn("예시 검색</strong> (등록 도메인: example.com)", result)
        self.assertNotIn("웹 검색에 이용하는 예시입니다.", result)
        self.assertNotIn("커뮤니티 게시판 예시입니다.", result)
        self.assertIn("분야별 용도, 등록 사이트 이름과 도메인", result)
        self.assertIn("이 분야 전체 등록 사이트 보기", result)
        self.assertIn("&lt;script&gt;위험&lt;/script&gt;", result)
        self.assertNotIn("<script>위험</script>", result)
        self.assertNotIn("검색·포털 97개", result)

    def test_built_directory_renders_all_real_category_examples_without_duplicates(self):
        root = Path(__file__).resolve().parents[1]
        records = json.loads((root / "assets/verified-directory.json").read_text(encoding="utf-8"))
        html = (root / "dist/directory.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('aria-label="분야별 사이트 목록 비교"'), 1)
        overview = html.split('aria-label="분야별 사이트 목록 비교"', 1)[1].split('<section aria-label="안전한 링크 이용"', 1)[0]
        from build import CATEGORY_LANDING
        for category, slug, _, _ in CATEGORY_LANDING:
            expected = next(record["name"] for record in records if record["category"] == category)
            self.assertIn(expected, overview)
            self.assertIn(f'/categories/{slug}', overview)
        self.assertIn('id="v6-results"', html)
        self.assertIn("분야별 용도, 등록 사이트 이름과 도메인", html)
        # The long descriptions remain once in their original static cards.
        # Do not duplicate them again inside the category overview.
        overview_only = html.split('class="lw-safety-note seo-directory-overview"', 1)[1].split('class="lw-safety-note seo-purpose-comparison"', 1)[0]
        self.assertNotIn("국내 만화 콘텐츠를 찾아볼 수 있는 마녀코믹스", overview_only)
        first = next(record for record in records if record["category"] == "검색·포털")
        self.assertIn(first["description"], html)

    def test_core_keywords_have_distinct_usable_homepage_paths(self):
        from build import core_search_intent_section
        section = core_search_intent_section(97)
        for term in ("주소모음", "링크모음", "사이트모음"):
            self.assertIn(f"<h3>{term}:", section)
        self.assertIn("현재 등록된 97개 사이트", section)
        self.assertIn('href="/directory"', section)
        self.assertIn('href="/categories/"', section)
        self.assertIn("목록 순서는 추천 순위가 아닙니다", section)
        with self.assertRaises(RuntimeError):
            core_search_intent_section(0)

    def test_built_homepage_primary_intent_section_is_unique_and_navigable(self):
        root = Path(__file__).resolve().parents[1]
        homepage = (root / "dist/index.html").read_text(encoding="utf-8")
        section_marker = 'aria-label="주소모음 링크모음 사이트모음 이용 안내"'
        self.assertEqual(homepage.count(section_marker), 1)
        section = homepage.split(section_marker, 1)[1].split('</section>', 1)[0]
        for term in ("주소모음", "링크모음", "사이트모음"):
            self.assertIn(f"<h3>{term}:", section)
        for target in ('href="/directory"', 'href="/categories/"'):
            self.assertIn(target, section)
        self.assertIn(f"{PUBLISHED_COUNT}개 사이트", section)

    def test_post_sitemap_date_comes_from_filename_not_filesystem_mtime(self):
        self.assertEqual(stable_post_lastmod(Path('seo-20261027-9c0ac627e0.md')), '2026-10-27')
        self.assertIsNone(stable_post_lastmod(Path('address-directory-safety-guide.md')))
        self.assertIsNone(stable_post_lastmod(Path('seo-20261377-bad.md')))

    def test_generated_canonical_and_og_use_nonredirecting_url(self):
        html = (
            '<link href="https://linkwiki.info/guides/address-check.html" rel="canonical">'
            '<meta property="og:url" content="https://linkwiki.info/guides/address-check.html">'
            '<a href="/guides/address-check.html">가이드</a>'
        )
        normalized = normalize_page_links(html)
        self.assertIn('href="https://linkwiki.info/guides/address-check" rel="canonical"', normalized)
        self.assertIn('content="https://linkwiki.info/guides/address-check"', normalized)
        self.assertIn('href="/guides/address-check"', normalized)
        self.assertNotIn('address-check.html', normalized)

    def test_category_breadcrumb_schema_uses_real_navigation_hierarchy(self):
        source = '<html><head><title>분야</title></head><body><h1>스포츠 링크모음</h1></body></html>'
        result = add_breadcrumb_data(source, '/categories/sports')
        block = re.search(r'<script type="application/ld\+json">(.*?)</script>', result)
        self.assertIsNotNone(block)
        schema = json.loads(block.group(1))
        self.assertEqual(schema['@type'], 'BreadcrumbList')
        self.assertEqual([entry['name'] for entry in schema['itemListElement']],
                         ['홈', '분야별 사이트', '스포츠 링크모음'])
        self.assertEqual(schema['itemListElement'][-1]['item'],
                         'https://linkwiki.info/categories/sports')

    def test_breadcrumb_schema_skips_home_and_is_idempotent(self):
        source = '<html><head></head><body><h1>주소 확인 방법</h1></body></html>'
        self.assertEqual(add_breadcrumb_data(source, '/'), source)
        result = add_breadcrumb_data(source, '/guides/address-check')
        self.assertEqual(add_breadcrumb_data(result, '/guides/address-check'), result)
        self.assertEqual(result.count('application/ld+json'), 1)

    def test_generated_pages_do_not_show_preview_notice(self):
        html = '<footer>링크위키 · 공개 전 미리보기. 외부 사이트는 별도 운영됩니다.</footer>'
        normalized = normalize_page_links(html)
        self.assertNotIn("공개 전 미리보기", normalized)
        self.assertIn("링크위키 · 사이트 주소와 이용 정보를 안내합니다.", normalized)

    def test_existing_evergreen_guide_titles_are_read(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "guides").mkdir()
            (root / "guides" / "sample.html").write_text(
                '<html><head><title>공식 주소 확인 방법 | 링크위키</title></head></html>',
                encoding="utf-8")
            with patch.object(auto_seo, "ROOT", root):
                self.assertEqual(auto_seo.static_guide_titles(), ["공식 주소 확인 방법"])


if __name__ == "__main__":
    unittest.main()
