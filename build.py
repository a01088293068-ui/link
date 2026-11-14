#!/usr/bin/env python3
"""Build LinkWiki's existing static pages plus a Markdown-driven guide journal.

Cloudflare Pages: build command `python3 build.py`; output directory `dist`.
No third-party dependencies, no external network calls, no overwrites of source.
"""
from datetime import datetime, timezone
import hashlib
from html import escape, unescape
from pathlib import Path
from urllib.parse import quote, urlparse
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
SITE = "https://linkwiki.info"
POSTS = ROOT / "content"

CATEGORY_LANDING = (
    ("커뮤니티", "community", "커뮤니티 사이트모음", "게임·취미·생활 등 관심사에 맞는 게시판을 찾아보고 가입 조건을 비교하세요."),
    ("한인교민", "korean", "해외 한인 사이트모음", "지역별 교민 정보와 생활 게시판을 살펴보고 실제 활동 도시를 확인하세요."),
    ("만화", "comics-directory", "만화·웹소설 사이트모음", "장르별 만화·웹소설 플랫폼의 작품 유형과 유료 이용 조건을 비교하세요."),
    ("만화·웹툰", "webtoon", "웹툰 링크모음", "웹툰 서비스별 작품 유형과 공식 이용 경로를 비교하세요."),
    ("AI 도구", "ai", "AI 도구 사이트모음", "글쓰기·검색·요약 도구를 기능과 이용 조건에 따라 비교하세요."),
    ("검색·포털", "search", "검색·포털 링크모음", "검색과 정보 탐색에 필요한 포털 서비스를 골라보세요."),
    ("스포츠", "sports", "스포츠 사이트모음", "일정·기록·뉴스 등 목적에 따라 서비스를 찾고 중계권을 확인하세요."),
    ("영상·OTT", "video", "영상·OTT 링크모음", "영상 서비스의 콘텐츠 제공 방식과 구독 조건을 구분해 살펴보세요."),
)


def apply_significant_lastmods(urlset, updates, ns):
    """Use explicit, verified substantive edit dates, never build/check-out time.

    Values stay stable on unrelated builds and must name a sitemap URL.
    """
    from datetime import date
    if not isinstance(updates, dict):
        raise RuntimeError("Significant page updates must be a JSON object")
    entries = {}
    for element in urlset.findall(f"{{{ns}}}url"):
        loc = element.find(f"{{{ns}}}loc")
        if loc is not None and loc.text:
            entries[loc.text] = element
    for path, day in updates.items():
        if not isinstance(path, str) or not path.startswith("/") or "?" in path or "#" in path:
            raise RuntimeError(f"Invalid significant-update path: {path}")
        if not isinstance(day, str) or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", day):
            raise RuntimeError(f"Invalid significant-update date: {path}")
        try:
            date.fromisoformat(day)
        except ValueError as error:
            raise RuntimeError(f"Invalid calendar date for: {path}") from error
        url = SITE + path
        if url not in entries:
            raise RuntimeError(f"Significantly changed page absent from sitemap: {url}")
        old = entries[url].find(f"{{{ns}}}lastmod")
        if old is None:
            old = ET.SubElement(entries[url], f"{{{ns}}}lastmod")
        if old.text and old.text > day:
            raise RuntimeError(f"Significant-update date predates sitemap date: {path}")
        old.text = day


def public_url(url):
    """Use Pages' extensionless public URL; keep files on disk as .html."""
    if url.startswith(SITE + "/"):
        prefix, tail = SITE, url[len(SITE):]
    elif url.startswith("/") and not url.startswith("//"):
        prefix, tail = "", url
    else:
        return url
    match = re.match(r"^([^?#]*)(.*)$", tail, re.S)
    path, suffix = match.groups()
    if path == "/index.html":
        path = "/"
    elif path.endswith(".html"):
        path = path[:-5]
    return prefix + path + suffix


def normalize_page_links(html):
    """Normalize existing same-site links and SEO metadata in generated HTML."""
    def href(match):
        value = match.group(2)
        if value.startswith(("https://", "http://", "mailto:", "//", "#")):
            updated = public_url(value)
        elif value.endswith(".html") or ".html#" in value or ".html?" in value:
            updated = re.sub(r"\.html(?=$|[?#])", "", value)
            if updated == "index":
                updated = "./"
            elif updated.endswith("/index"):
                updated = updated[:-5]
        else:
            updated = value
        return match.group(1) + updated + match.group(3)

    html = re.sub(r'(\bhref=")([^"]+)(")', href, html)
    html = re.sub(r'(<meta\s+[^>]*\bproperty="og:url"[^>]*\bcontent=")([^"]+)(")',
                  lambda m: m.group(1) + public_url(m.group(2)) + m.group(3), html)
    html = re.sub(r'(<meta\s+[^>]*\bcontent=")([^"]+)("[^>]*\bproperty="og:url")',
                  lambda m: m.group(1) + public_url(m.group(2)) + m.group(3), html)
    # Remove an obsolete pre-publication notice from generated public pages.
    # Source HTML is preserved; only the deployed output is normalized.
    html = html.replace("링크위키 · 공개 전 미리보기.",
                        "링크위키 · 사이트 주소와 이용 정보를 안내합니다.")
    return html


def clean_url(url):
    url = url.strip()
    if url.startswith("/") and not url.startswith("//"):
        return url
    if url.startswith("#"):
        return url
    parsed = urlparse(url)
    if parsed.scheme in ("https", "http", "mailto") and (parsed.netloc or parsed.scheme == "mailto"):
        return url
    return "#"


def inline(text):
    placeholders = []
    def hold(markup):
        marker = f"ZXHTMLTOKEN{len(placeholders)}ZX"
        placeholders.append((marker, markup))
        return marker
    def replace_anchor(match):
        return hold(f'<a href="{escape(clean_url(match.group(2)), quote=True)}" rel="noopener noreferrer">{escape(match.group(3))}</a>')
    text = re.sub(r'<a\s+href\s*=\s*[\'\"]([^\'\"]+)[\'\"][^>]*>(.*?)</a>',
                  lambda m: hold(f'<a href="{escape(clean_url(m.group(1)), quote=True)}" rel="noopener noreferrer">{escape(re.sub("<[^>]+>", "", m.group(2)))}</a>'),
                  text, flags=re.I | re.S)
    text = re.sub(r'\[([^\]]{1,200})\]\(([^\s)]+)\)',
                  lambda m: hold(f'<a href="{escape(clean_url(m.group(2)), quote=True)}" rel="noopener noreferrer">{escape(m.group(1))}</a>'), text)
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    for marker, markup in placeholders:
        text = text.replace(marker, markup)
    return text


def markdown(body):
    """Render the supported subset of Markdown, including accessible tables.

    Escape all article text through inline(); malformed tables remain text
    instead of emitting broken HTML or silently losing article content.
    """
    chunks, paragraph, list_items, list_type = [], [], [], None
    def flush_paragraph():
        if paragraph:
            chunks.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    def flush_list():
        nonlocal list_type
        if list_items:
            tag = list_type or "ul"
            chunks.append('<' + tag + '>' + ''.join('<li>' + inline(i) + '</li>' for i in list_items) + '</' + tag + '>')
            list_items.clear()
        list_type = None
    def cells(row):
        return [value.strip() for value in row.strip().strip('|').split('|')]
    lines = body.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        # A Markdown table requires a header and separator row with the same
        # number of columns. Single-line pipes in ordinary prose are ignored.
        if line.startswith('|') and index + 1 < len(lines):
            headers = cells(line)
            separators = cells(lines[index + 1]) if lines[index + 1].strip().startswith('|') else []
            if (len(headers) >= 2 and len(separators) == len(headers)
                    and all(re.fullmatch(r':?-{3,}:?', item) for item in separators)):
                flush_paragraph()
                flush_list()
                index += 2
                data_rows = []
                while index < len(lines) and lines[index].strip().startswith('|'):
                    values = cells(lines[index])
                    if len(values) != len(headers):
                        break
                    data_rows.append('<tr>' + ''.join('<td>' + inline(value) + '</td>'
                                                     for value in values) + '</tr>')
                    index += 1
                chunks.append(
                    '<div class="blog-table-scroll"><table><thead><tr>' +
                    ''.join('<th scope="col">' + inline(value) + '</th>' for value in headers) +
                    '</tr></thead><tbody>' + ''.join(data_rows) +
                    '</tbody></table></div>')
                continue
        index += 1
        if not line:
            flush_paragraph(); flush_list(); continue
        if re.fullmatch(r'-{3,}|\*{3,}', line):
            flush_paragraph(); flush_list(); chunks.append('<hr>'); continue
        heading = re.match(r'^(#{1,5})\s+(.+)$', line)
        if heading:
            flush_paragraph(); flush_list()
            depth = len(heading.group(1))
            chunks.append(f'<h{depth}>{inline(heading.group(2))}</h{depth}>'); continue
        bullet = re.match(r'^(?:[-*+]\s+|\d+[.)]\s+)(.*)$', line)
        if bullet:
            flush_paragraph()
            desired = 'ol' if re.match(r'^\d', line) else 'ul'
            if list_type and desired != list_type:
                flush_list()
            list_type = desired
            list_items.append(bullet.group(1)); continue
        flush_list()
        paragraph.append(line)
    flush_paragraph(); flush_list()
    return '\n'.join(chunks)


def extract_title(body):
    match = re.search(r'^#\s+(.+)$', body, flags=re.M)
    return match.group(1).strip() if match else "링크위키 이용 가이드"


def excerpt(body):
    text = re.sub(r'<[^>]*>', '', body)
    text = re.sub(r'[#*`\[\]()>_\-]+', ' ', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return (text[:140].rstrip() + '…') if len(text) > 140 else text


def stable_post_lastmod(path):
    """Use a date embedded in an article filename, never checkout mtime.

    GitHub Actions checkout updates filesystem mtimes even when content is unchanged.
    Undated posts have no reliable modification date, so omit lastmod.
    """
    match = re.search(r"(?:^|[-_])(20\d{6})(?:[-_.]|$)", path.stem)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def slug_for(path):
    # Existing GitHub filenames already provide stable, ASCII URLs.
    return re.sub(r'[^a-zA-Z0-9_-]', '-', path.stem).strip('-')[:90] or "article"


def chrome():
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    header = re.search(r'<header class="top">.*?</header>', source, re.S).group()
    header = add_nav(header)
    footer = re.search(r'<footer class="footer">.*?</footer>', source, re.S).group()
    # Blog is nested; force absolute paths for reusable site chrome.
    for relative in ("index.html", "directory.html", "about.html", "privacy.html",
                     "favicon.png", "assets/header-wordmark.png", "guides/address-check.html",
                     "guides/security.html"):
        header = header.replace('"' + relative + '"', '"/' + relative + '"')
        footer = footer.replace('"' + relative + '"', '"/' + relative + '"')
    header = re.sub(r'href="(assets/[^\"]+)"', r'href="/\1"', header)
    return header, footer


def add_nav(source):
    """Append one discreet site-info item to the existing desktop/mobile menu."""
    pattern = r'(<nav\b[^>]*id="mobile-primary-nav"[^>]*>)(.*?)(</nav>)'
    def replace(match):
        if 'href="/blog/"' in match.group(2):
            return match.group()
        return match.group(1) + match.group(2) + '<a href="/blog/">사이트 정보</a>' + match.group(3)
    return re.sub(pattern, replace, source, count=1, flags=re.S)


def polish_home_intent(home):
    """Small, restrained changes to the generated home page; source HTML stays intact."""
    records = json.loads((ROOT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise RuntimeError("Homepage needs nonempty published directory records")
    total_sites = len(records)
    # Sync both metadata and visible content before applying exact layout edits.
    # This avoids publishing a stale H1/OG description after adding real listings.
    home = re.sub(r"\b\d+개(?=\s+(?:등록\s+)?(?:사이트|항목))",
                  f"{total_sites}개", home)
    home = re.sub(r"(등록 사이트\s+)\d+개",
                  lambda match: match.group(1) + f"{total_sites}개", home)
    # Submitting the homepage search must use the indexable canonical,
    # not a legacy .html address which may redirect before filtering.
    legacy_form = '<form action="directory.html" class="lw-search" method="get" role="search">'
    canonical_form = '<form action="/directory" class="lw-search" method="get" role="search">'
    if home.count(legacy_form) == 1:
        home = home.replace(legacy_form, canonical_form, 1)
    elif home.count(canonical_form) != 1:
        raise RuntimeError("Homepage structure changed: search form action; review required")
    edits = (
        (
            '분야별 사이트를 비교하고, 주소 확인부터 접속 문제 해결까지 링크위키에서 살펴보세요.',
            '링크위키 주소모음·링크모음에서 분야별 사이트를 찾고, 실제 이동 주소와 이용 조건을 확인해 보세요.',
        ),
        ('<label for="lw-home-query">사이트 이름으로 찾기</label>',
         '<label for="lw-home-query">사이트 이름·주소 검색</label>'),
        (
            f'이 사이트의 {total_sites}개 등록 항목을 이름·분야·도메인으로 검색합니다.</p>',
            f'이 사이트의 {total_sites}개 등록 항목을 이름·분야·도메인으로 검색합니다.</p>'
            '<p class="lw-search-quicklinks"><a href="/directory.html">전체 주소 목록 보기</a>'
            ' · <a href="/categories/">분야별 사이트 찾기</a></p>',
        ),
        (
            '<p class="v47-help-note">사이트 목록은 편의를 위한 안내이며, 외부 서비스의 운영·안전성을 보증하지 않습니다. 접속 전 주소와 이용 조건을 확인하세요.</p>',
            '<p class="v47-help-note">등록된 주소는 변경되거나 접속되지 않을 수 있으며, 실시간 접속 확인을 보증하지 않습니다. '
            '방문 전 <a href="/guides/address-check.html">공식 주소 확인 방법</a>과 각 서비스의 이용 조건을 확인하세요.</p>',
        ),
    )
    for old, new in edits:
        if home.count(old) == 1:
            home = home.replace(old, new, 1)
        elif home.count(new) == 1:
            # The source page may already include this editorial improvement.
            continue
        elif old.startswith("분야별 사이트를 비교하고,"):
            # The homepage now uses a more specific, fact-checked directory summary.
            if (f"{total_sites}개 등록 사이트를 분야별로 검색하고 비교하세요." not in home
                    and f"{total_sites}개 등록 사이트 설명과 이동 주소를 한곳에서 비교할 수 있습니다." not in home):
                raise RuntimeError("Homepage structure changed; SEO intent adjustment needs review")
        else:
            raise RuntimeError("Homepage structure changed; SEO intent adjustment needs review")
    return home


def document(title, description, canonical, main_content, header, footer):
    description = description[:170]
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow"><title>{escape(title)} | 링크위키</title>
<meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{escape(canonical, quote=True)}">
<meta property="og:type" content="article"><meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(description, quote=True)}">
<meta property="og:url" content="{escape(canonical, quote=True)}">
<link rel="icon" href="/favicon.png" type="image/png">
<link rel="stylesheet" href="/assets/style.css?v=final-cta"><link rel="stylesheet" href="/assets/blog.css">
</head><body><a class="skip" href="#main">본문으로 이동</a>{header}
<main id="main">{main_content}</main>{footer}
<script defer src="/assets/site.js"></script><script defer src="/assets/mobile-menu.js"></script>
</body></html>'''


def add_breadcrumb_data(html, public_path):
    """Add truthful hierarchy metadata to existing navigable guide/category pages."""
    segments = public_path.strip("/").split("/")
    if segments[0] not in {"categories", "guides", "blog"} or public_path == "/blog/":
        return html
    if 'type="application/ld+json"' in html:
        return html
    heading = re.search(r'<h1\b[^>]*>(.*?)</h1>', html, re.S | re.I)
    if not heading:
        raise RuntimeError(f"Breadcrumb page missing heading: {public_path}")
    page_name = unescape(re.sub(r'<[^>]+>', '', heading.group(1))).strip()
    if not page_name:
        raise RuntimeError(f"Breadcrumb page has blank heading: {public_path}")
    items = [{"@type": "ListItem", "position": 1, "name": "홈", "item": SITE + "/"}]
    if segments[0] == "categories" and public_path != "/categories/":
        items.append({"@type": "ListItem", "position": 2, "name": "분야별 사이트",
                      "item": SITE + "/categories/"})
    elif segments[0] == "blog" and public_path != "/blog/":
        items.append({"@type": "ListItem", "position": 2, "name": "사이트 탐색 정보",
                      "item": SITE + "/blog/"})
    items.append({"@type": "ListItem", "position": len(items) + 1,
                  "name": page_name, "item": SITE + public_path})
    schema = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": items}
    block = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c") + '</script>'
    if html.count("</head>") != 1:
        raise RuntimeError(f"Breadcrumb page missing head: {public_path}")
    return html.replace("</head>", block + "</head>", 1)



def core_search_intent_section(total_sites):
    """One useful homepage entry point for the three primary search intents."""
    if total_sites < 1:
        raise RuntimeError("Homepage keyword guide needs real directory records")
    return (
        '<section class="wrap seo-core-intent" aria-label="주소모음 링크모음 사이트모음 이용 안내">'
        '<div class="v47-section-heading"><h2>주소모음·링크모음·사이트모음 이용하기</h2></div>'
        '<p>링크위키는 사이트 이름과 도메인, 분야별 목록을 탐색하는 서비스입니다. '
        f'현재 등록된 {total_sites}개 사이트를 검색하거나 분야별로 살펴볼 수 있습니다. '
        '검색 결과에 표시된 주소의 공식성이나 현재 접속 가능 여부는 별도로 확인하세요.</p>'
        '<div class="v6-grid">'
        '<article class="v6-card"><h3>주소모음: 사이트 주소 찾기</h3>'
        '<p>도메인이나 사이트 이름을 알고 있다면 목록 검색을 사용하세요. '
        '검색 결과에서 설명과 연결 주소를 확인한 뒤 방문할 수 있습니다.</p>'
        '<a href="/directory">주소모음에서 주소 검색하기</a></article>'
        '<article class="v6-card"><h3>링크모음: 분야별 링크 탐색</h3>'
        '<p>관심 분야부터 고르면 해당 분야에 등록된 링크와 간단한 서비스 설명을 볼 수 있습니다.</p>'
        '<a href="/categories/">링크모음 분야별 보기</a></article>'
        '<article class="v6-card"><h3>사이트모음: 사이트별 이용 목적 비교</h3>'
        '<p>전체 목록에서 사이트 이름과 제공 기능에 관한 등록 설명을 비교하고 '
        '필요한 서비스를 찾아보세요. 목록 순서는 추천 순위가 아닙니다.</p>'
        '<a href="/directory">사이트모음 전체 목록 비교하기</a></article>'
        '</div></section>'
    )


def sync_directory_count(html, total_sites):
    """Update SEO copy and visible directory count using actual published records."""
    if total_sites < 1:
        raise RuntimeError("Directory count requires nonempty verified records")
    # Do not modify category counts such as '8개 분야'.
    html, inline_count = re.subn(
        r"\b\d+개(?=\s+(?:등록\s+)?사이트(?:의|를|\b))",
        lambda _: f"{total_sites}개", html,
    )
    html, status_count = re.subn(
        r"(등록 사이트\s+)\d+개",
        lambda m: m.group(1) + f"{total_sites}개", html,
    )
    if inline_count < 5 or status_count != 1:
        raise RuntimeError("Directory SEO count markers changed; review required")
    return html


def homepage_directory_examples(records, categories):
    """Keep the homepage a short navigation hub, not a second full directory.

    The canonical /directory remains the place for detailed per-site
    descriptions, hosts, search, filters and comparison tools. Homepage cards
    show five verified, independently named destinations per category, so users
    arriving via an already-indexed homepage can reach more sites directly.
    """
    if not isinstance(records, list) or not records:
        raise RuntimeError("Homepage examples require verified directory data")
    cards = []
    for category, slug, heading, purpose in categories:
        entries = [
            item for item in records
            if isinstance(item, dict) and item.get("category") == category
            and isinstance(item.get("name"), str) and item["name"].strip()
            and isinstance(item.get("description"), str) and item["description"].strip()
        ][:5]
        if not entries:
            raise RuntimeError(f"Missing descriptive directory example: {category}")
        for entry in entries:
            parsed = urlparse(str(entry.get("url", "")))
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise RuntimeError(f"Invalid registered example URL: {category}")
        # A real user can open a registered service directly from the
        # indexed homepage. Five per category remain a curated small fraction
        # of the unique exhaustive /directory collection.
        examples = " · ".join(
            '<a href="' + escape(item["url"], quote=True) +
            '" target="_blank" rel="noopener noreferrer external" aria-label="' +
            escape(item["name"].strip(), quote=True) +
            ' 등록 사이트 새 창에서 열기">' +
            escape(item["name"].strip()) + '</a>'
            for item in entries
        )
        cards.append(
            '<article class="v6-card">'
            f'<h3><a href="/categories/{escape(slug, quote=True)}">{escape(heading)}</a></h3>'
            f'<p>{escape(purpose)}</p>'
            f'<p class="home-example-names">등록 예시: {examples}</p>'
            f'<a href="/categories/{escape(slug, quote=True)}">이 분야 사이트 더 보기</a>'
            '</article>'
        )
    return (
        '<section class="wrap seo-directory-examples" aria-label="분야별 사이트 탐색 길잡이">'
        '<div class="v47-section-heading"><h2>관심 분야부터 찾기</h2></div>'
        '<p>첫 화면에서 관심 분야를 선택하거나 등록된 사이트를 바로 열 수 있습니다. '
        '전체 도메인·상세 설명·검색·직접 비교는 '
        '<a href="/directory">전체 주소모음 목록</a>에서 확인하세요. '
        '외부 연결은 등록된 주소로 이동할 뿐 공식성·실시간 접속·안전성을 보증하지 않습니다. '
        '아래 예시는 인기 순위나 안전 등급이 아닙니다.</p>'
        '<div class="v6-grid">' + ''.join(cards) + '</div></section>'
    )

RELATED_CATEGORY_PATHS = {
    "community": (("sports", "스포츠 일정과 기록 찾기"),
                  ("search", "검색·포털 서비스 살펴보기")),
    "korean": (("search", "생활 정보 검색 서비스 찾기"),
               ("community", "관심사별 커뮤니티 살펴보기")),
    "comics-directory": (("webtoon", "웹툰 연재 플랫폼 보기"),
                          ("video", "영상 서비스도 비교하기")),
    "webtoon": (("comics-directory", "만화·웹소설 서비스 찾기"),
               ("video", "영상·OTT 서비스 살펴보기")),
    "ai": (("search", "검색·포털 서비스 비교하기"),
           ("community", "정보 공유 커뮤니티 살펴보기")),
    "search": (("ai", "AI 검색·질의응답 도구 보기"),
              ("korean", "해외 한인 생활 정보 찾기")),
    "sports": (("community", "스포츠 커뮤니티 찾기"),
               ("video", "영상·OTT 서비스 비교하기")),
    "video": (("sports", "스포츠 일정·결과 확인하기"),
              ("webtoon", "웹툰 콘텐츠 플랫폼 보기")),
}



# Distinct editorial guidance is written for the visitor's actual task.
# It is not a paraphrase of the registered site descriptions, a fake ranking,
# or an unverified statement that a third-party service is currently available.
CATEGORY_DECISION_GUIDES = {
    "community": (
        ("관심사에 맞는 게시판을 찾는 경우",
         "게임·취미·일상처럼 다루는 주제를 먼저 정한 뒤 게시물의 실제 활동 시점, 새 글의 주제와 가입 조건을 확인하세요. 규모가 큰 커뮤니티라도 원하는 주제의 게시판은 조용할 수 있습니다."),
        ("중고 거래나 지역 정보가 필요한 경우",
         "일반 토론 게시판과 거래 게시판을 구분하세요. 판매자 신원 확인, 안전 결제 수단, 직접 만남 장소 등은 해당 서비스의 공지와 이용 규칙을 따라 점검하세요."),
        ("정보의 진위를 확인하려는 경우",
         "익명 게시글·댓글은 이용 경험일 수 있으나 공식 발표가 아닙니다. 게시 날짜와 근거 자료를 확인하고 중요한 내용은 기관·운영사의 원문과 대조하세요.")),
    "korean": (
        ("거주 도시의 생활 정보를 찾는 경우",
         "국가 단위 안내와 도시별 게시판을 구분하세요. 같은 나라라도 주거·교통·학교·행정 절차는 도시와 지역에 따라 다를 수 있습니다."),
        ("비자·행정 정보를 확인하려는 경우",
         "교민 게시글의 경험담을 최신 규정으로 받아들이지 마세요. 관할 대사관·이민국 등 공공기관의 공식 안내와 신청 날짜를 별도로 확인하세요."),
        ("구인·주거 정보를 살펴보는 경우",
         "게시 날짜, 실제 지역, 연락 방식과 수수료 조건을 확인하세요. 서류 사본이나 계약금을 요청하는 게시글은 서비스 운영 정책과 신뢰할 수 있는 공식 경로를 먼저 검토하세요.")),
    "comics-directory": (
        ("읽고 싶은 작품이 정해진 경우",
         "작품 이름과 제공 플랫폼을 확인하고 웹툰·전자책·웹소설 중 어떤 형식인지 구분하세요. 같은 제목이라도 판본이나 이용 형태가 다를 수 있습니다."),
        ("장르를 둘러보는 경우",
         "로맨스·무협·판타지 등 선호 장르를 먼저 정하고 회차형 서비스와 단행본형 서비스를 나누어 살펴보세요. 첫 화면의 노출 순서는 작품 품질 평가가 아닙니다."),
        ("무료와 유료 이용 조건을 비교하는 경우",
         "일부 무료 회차, 대여, 소장, 정기 구독은 서로 다른 조건입니다. 실제 결제 전에 열람 기간과 청소년 이용 제한을 해당 플랫폼에서 확인하세요.")),
    "webtoon": (
        ("연재 중인 작품을 따라보는 경우",
         "연재 요일, 휴재 공지, 최신 회차 공개 방식과 플랫폼 계정 조건을 확인하세요. 광고에 표시된 공개일과 실제 작품 페이지의 일정이 다를 수 있습니다."),
        ("한 번에 완결 작품을 읽고 싶은 경우",
         "완결 여부와 회차 구성, 대여·소장 옵션을 확인하세요. 무료 미리보기만으로 전체 작품이 무료라고 판단하지 마세요."),
        ("만화·웹소설과 비교하는 경우",
         "세로형 웹툰, 페이지형 만화, 텍스트 웹소설은 읽는 방식이 다릅니다. 콘텐츠 형식부터 구분한 후 선호 장르에 맞는 서비스를 살펴보세요.")),
    "ai": (
        ("글쓰기나 아이디어 정리가 필요한 경우",
         "초안의 문체·한국어 표현·재작성 편의성을 비교하고, 결과물에 잘못된 사실이 없는지 직접 검토하세요. 같은 질문을 여러 도구에 입력해 비교할 수 있습니다."),
        ("자료 조사와 출처 확인이 중요한 경우",
         "답변에 인용된 원문 링크가 실제 주장과 일치하는지 확인하세요. AI가 제시한 문헌이나 통계가 존재한다는 보장은 없습니다."),
        ("문서·파일을 입력하려는 경우",
         "지원 파일 형식, 업로드 제한, 저장·학습 관련 설정을 서비스별로 확인하세요. 비밀번호나 고객 정보 등 민감한 내용은 업로드하지 않는 편이 안전합니다.")),
    "search": (
        ("정부 민원·복지·연금·건강보험 서비스를 찾는 경우",
         "정부24는 민원 신청·발급, 복지로는 복지서비스, 한국장학재단은 장학금·학자금 지원 정보를 안내합니다. 건강보험 자격·검진은 국민건강보험공단, 연금 제도는 국민연금공단, 질병·건강 자료는 국가건강정보포털, 의료기관·의약품 정보는 건강보험심사평가원에서 목적에 따라 찾아보세요. 국민신문고는 민원 접수, 위택스는 지방세 신고·납부에 적합합니다. 자격과 신청 조건은 각 기관에서 다시 확인해야 합니다."),
        ("국내 논문·사전·통계·법령을 찾는 경우",
         "학술연구정보서비스 RISS는 학술자료, 국립중앙도서관·국가전자도서관은 도서·전자자료, 표준국어대사전은 우리말 뜻풀이, 국가통계포털 KOSIS는 통계표, 국가법령정보센터는 법령 검색에 적합합니다. 자료의 발행일과 적용 시점은 서비스에서 다시 확인하세요."),
        ("창업 지원·특허·무역 신고 사이트를 찾는 경우",
         "창업지원사업 공고는 K-Startup 창업지원포털과 기업마당을, 특허·상표 정보를 검색하려면 KIPRIS 지식재산정보검색을, 전자출원과 등록 업무는 특허로를 이용하세요. 통관·관세 신고는 관세청 유니패스, 기업·경제 자료는 대한상공회의소 코참넷이 목적에 맞습니다. 검색 결과의 광고가 공식 운영 도메인임을 보증하지 않으므로 각 기관의 이용 안내를 확인하세요.")),
    "sports": (
        ("경기 시작 시간과 일정을 확인하는 경우",
         "경기장 현지 시간대와 내 지역 시간대를 구분하고 연기·취소 공지를 확인하세요. 일정 제공 사이트와 실제 주최 측 공지의 반영 시차가 있을 수 있습니다."),
        ("실시간 점수와 기록을 확인하는 경우",
         "종목·리그를 먼저 선택하고 업데이트 지연 여부를 살펴보세요. 중계 영상이 아닌 점수·통계 제공 서비스인지 구분해야 합니다."),
        ("실제 중계 시청을 찾는 경우",
         "점수 사이트가 영상 중계권도 가진 것은 아닙니다. 해당 리그 또는 공식 중계권 보유 서비스의 지역 제한·구독 조건을 확인하세요.")),
    "video": (
        ("영화·드라마를 정주행하려는 경우",
         "원하는 작품이 현재 거주 지역에서 제공되는지 플랫폼 내 검색으로 확인하세요. 제공 작품은 시점과 지역에 따라 달라질 수 있습니다."),
        ("요금과 이용 방식을 비교하는 경우",
         "무료 광고형 시청, 개별 대여, 정기 구독을 구분하고 화질·동시 접속·해지 조건을 각 서비스에서 확인하세요."),
        ("가족·어린이와 함께 이용하는 경우",
         "연령 제한, 보호자 설정, 자막·더빙 옵션을 확인하세요. 앱이나 웹사이트에서 가능한 기능이 기기마다 다를 수 있습니다.")),
}


# Curated Korean-first examples for the eight existing categories, not a popularity ranking.
# Every service must remain present in the registered catalogue.
CATEGORY_SEARCH_EXAMPLES = {
    "community": ("인벤", "디시인사이드"),
    "korean": ("(전세계)코리안넷", "(미국)미주중앙일보"),
    "comics-directory": ("조아라", "노벨피아"),
    "webtoon": ("네이버 웹툰", "카카오웹툰"),
    "ai": ("뤼튼", "미리캔버스"),
    "search": ("네이버", "정부24"),
    "sports": ("네이버 스포츠", "KBO 공식 홈페이지"),
    "video": ("티빙", "웨이브"),
}


def category_decision_guide(slug, records, categories=CATEGORY_LANDING):
    """Add original, task-specific advice while grounding examples in the list."""
    catalog = {item_slug: category for category, item_slug, _, _ in categories}
    topics = CATEGORY_DECISION_GUIDES.get(slug)
    if slug not in catalog or not topics or len(topics) != 3:
        raise RuntimeError(f"Category editorial guidance missing: {slug}")
    present = {
        item["name"].strip()
        for item in records
        if isinstance(item, dict) and item.get("category") == catalog[slug]
        and isinstance(item.get("name"), str) and item["name"].strip()
    }
    examples = CATEGORY_SEARCH_EXAMPLES.get(slug, ())
    if len(examples) != 2 or not all(name in present for name in examples):
        raise RuntimeError(f"Insufficient sourced category examples: {slug}")
    items = ''.join(
        '<li><h3>' + escape(heading) + '</h3><p>' + escape(advice) + '</p></li>'
        for heading, advice in topics)
    return (
        '<section class="wrap seo-related-links seo-category-decision" '
        'aria-label="이 분야의 목적별 선택 방법">'
        '<h2>이 분야에서 사이트를 선택하는 방법</h2>'
        '<p>목록에 실제 등록된 '
        '<a href="/directory?q=' + quote(examples[0], safe="") + '">' + escape(examples[0]) + '</a>, '
        '<a href="/directory?q=' + quote(examples[1], safe="") + '">' + escape(examples[1]) + '</a>'
        ' 등을 살펴보기 전에 '
        '내가 필요한 기능을 정하고 비교 기준을 확인하세요. '
        '이름이 등록됐다는 사실은 최신 접속 상태나 공식 인증을 보증하지 않습니다.</p>'
        '<ol>' + items + '</ol>'
        '<p><a href="/guides/address-check">사이트 주소 확인 방법</a> · '
        '<a href="/directory">전체 등록 사이트에서 다시 검색</a></p>'
        '</section>'
    )


def related_category_navigation(slug):
    """Two genuine follow-on categories per landing page, never fabricated URLs."""
    valid = {path for _, path, _, _ in CATEGORY_LANDING}
    neighbors = RELATED_CATEGORY_PATHS.get(slug)
    if slug not in valid or not neighbors or len(neighbors) != 2:
        raise RuntimeError(f"Unconfigured related categories: {slug}")
    if any(other not in valid or other == slug for other, _ in neighbors):
        raise RuntimeError(f"Invalid related category links: {slug}")
    return (
        '<section class="wrap seo-related-links" aria-label="연관 분야 이어서 찾기">'
        '<h2>함께 살펴볼 분야</h2>'
        '<p>현재 분야와 함께 비교하기 좋은 다른 사이트 목록입니다.</p>'
        '<ul>' + ''.join(
            f'<li><a href="/categories/{escape(other, quote=True)}">'
            f'{escape(label)}</a></li>'
            for other, label in neighbors
        ) + '</ul></section>'
    )



DIRECTORY_PURPOSE_COMPARISONS = (
    ("경기 결과 확인과 영상 시청은 다른 작업입니다",
     ("sports", "스포츠 일정·기록"), ("video", "영상·OTT"),
     "경기 시작 시간과 점수만 필요하면 스포츠 정보 사이트를 먼저 보세요. "
     "실제 경기 영상을 시청하려면 별도로 공식 중계권 보유 서비스와 지역별 시청 조건을 확인해야 합니다."),
    ("AI 답변과 검색 원문을 구분해 활용하세요",
     ("ai", "AI 질문·요약"), ("search", "검색·포털"),
     "초안 작성과 긴 내용 요약에는 AI 도구를 비교하고, 확인 가능한 출처·최신 발표가 필요한 내용은 "
     "검색·포털의 원문에서 발행일과 작성 주체를 검토하세요."),
    ("웹툰 연재와 만화·웹소설 이용 방식이 다릅니다",
     ("webtoon", "웹툰 연재 플랫폼"), ("comics-directory", "만화·웹소설"),
     "요일별 연재 웹툰을 찾는지, 만화 단행본이나 웹소설을 읽으려는지 먼저 정하세요. "
     "대여·소장 기간과 이용 요금은 선택한 작품의 실제 페이지에서 확인해야 합니다."),
    ("지역 생활 질문과 관심사별 토론을 나눠 찾으세요",
     ("korean", "해외 한인 생활"), ("community", "주제별 커뮤니티"),
     "해외 취업·거주·정착 질문이라면 현지 지역이 명확한 한인 정보부터 살펴보고, "
     "취미나 IT 등 주제별 경험은 커뮤니티에서 찾아보세요. 중요한 행정 규정은 공식 기관 공지를 우선합니다."),
)


def directory_purpose_comparison(records, categories):
    """Original cross-category decisions, backed by actual registered entries."""
    valid = {slug: category for category, slug, _, _ in categories}
    if len(DIRECTORY_PURPOSE_COMPARISONS) != 4:
        raise RuntimeError("Directory purpose comparisons incomplete")
    articles = []
    for title, (left_slug, left_label), (right_slug, right_label), advice in DIRECTORY_PURPOSE_COMPARISONS:
        if left_slug not in valid or right_slug not in valid or left_slug == right_slug:
            raise RuntimeError("Directory purpose comparison links invalid")
        examples = []
        for slug in (left_slug, right_slug):
            found = next((item["name"] for item in records
                          if isinstance(item, dict)
                          and item.get("category") == valid[slug]
                          and isinstance(item.get("name"), str)
                          and item["name"].strip()), None)
            if not found:
                raise RuntimeError(f"Directory comparison site example missing: {slug}")
            examples.append(found)
        articles.append(
            '<article class="seo-purpose-pair">'
            '<h3>' + escape(title) + '</h3>'
            '<p>' + escape(advice) + '</p>'
            '<p><a href="/categories/' + escape(left_slug, quote=True) + '">'
            + escape(left_label) + '</a> (등록 예시: ' + escape(examples[0]) + ') · '
            '<a href="/categories/' + escape(right_slug, quote=True) + '">'
            + escape(right_label) + '</a> (등록 예시: ' + escape(examples[1]) + ')</p>'
            '</article>'
        )
    return (
        '<section id="site-purpose-comparison" class="lw-safety-note seo-purpose-comparison" '
        'aria-label="이용 목적별 사이트 비교">'
        '<h2>필요한 일부터 정하는 사이트모음 선택법</h2>'
        '<p>같은 주소모음 목록에 등록되어 있어도 사이트마다 쓰임새가 다릅니다. '
        '아래는 실제 등록 분야를 목적별로 비교하는 방법이며 인기 순위나 추천 등급이 아닙니다.</p>'
        + ''.join(articles) + '</section>'
    )


def directory_relevant_guides(posts):
    """Visible contextual guide entry points using only published article URLs."""
    intents = (
        ("주소모음에서 원하는 사이트를 더 정확히 찾으려면?", ("주소모음 검색 실전 가이드",)),
        ("링크모음과 사이트모음을 어떤 기준으로 비교하나요?", ("링크모음·사이트모음 비교 기준",)),
        ("검색 결과가 없으면 어떻게 다시 찾나요?", ("주소모음 검색 결과가 없을 때",)),
        ("서비스를 실제 용도로 비교하려면?", ("사이트모음 선택 방법",)),
        ("휴대전화에서는 주소를 어떻게 확인하나요?", ("모바일 주소모음 이용법",)),
        ("국세와 지방세 서비스는 어디에서 구분하나요?", ("홈택스와 위택스 차이",)),
        ("행정 증명서와 민원 제안은 어디로 가나요?", ("정부24와 국민신문고 차이",)),
        ("공공데이터 파일과 통계표는 어떻게 다른가요?", ("공공데이터포털과 KOSIS 차이", "공공데이터포털과 KOSIS 선택법")),
        ("웹툰과 웹소설 원작은 어디에서 찾나요?", ("국내 웹툰 사이트모음",)),
        ("KBO·K리그 일정과 해외 경기 점수는 어디서 보나요?", ("스포츠 사이트모음: KBO",)),
        ("해외 경기 시간이 다른 날짜로 보이면 어떻게 하나요?", ("해외 스포츠 경기 한국 시간 확인법",)),
        ("해외 한인 생활정보를 지역별로 어디서 찾나요?", ("해외 한인 사이트모음",)),
        ("취업·장학금·복지 정보는 어떻게 찾나요?", ("고용24·한국장학재단·복지로 구분",)),
        ("글쓰기·번역·디자인 AI는 어떻게 고르나요?", ("한국어 AI 사이트모음 선택법",)),
        ("검색한 두 사이트를 나란히 비교하려면?", ("검색 결과에서 두 사이트 비교하기",)),
        ("사이트모음은 어떤 기준으로 비교하나요?", ("비교 기준", "사이트모음 비교")),
        ("광고 링크는 어떻게 구분하나요?", ("광고 구분", "광고")),
    )
    items = []
    used = set()
    for question, tokens in intents:
        chosen = next((post for post in posts
                       if post.get("url") not in used
                       and any(token in post.get("title", "") for token in tokens)
                       and post.get("url", "").startswith("/blog/")
                       and post.get("title")), None)
        if chosen is None:
            continue
        used.add(chosen["url"])
        items.append(
            '<li><strong>' + escape(question) + '</strong> '
            '<a href="' + escape(chosen["url"], quote=True) + '">'
            + escape(chosen["title"]) + '</a></li>'
        )
    if len(items) < 2:
        raise RuntimeError("Directory needs two distinct, published task-specific guides")
    return (
        '<section id="site-related-guides" class="lw-safety-note seo-directory-guides" '
        'aria-label="목적에 맞는 실제 이용 가이드">'
        '<h2>사이트 목록을 더 정확하게 이용하는 방법</h2>'
        '<p>찾을 주소가 없거나 두 사이트를 비교해야 한다면, '
        '아래 실제 발행된 안내 글에서 점검 순서를 확인하세요.</p>'
        '<ul>' + ''.join(items) + '</ul>'
        '<p><a href="/blog/">다른 이용 가이드 모두 보기</a></p>'
        '</section>'
    )


# Real services helpful to Korean users, intentionally curated instead of
# claiming a measured popularity or safety ranking.
KOREAN_FIRST_SEARCH_NAMES = (
    "뤼튼", "미리캔버스", "카카오맵", "국가법령정보센터",
    "대한축구협회", "치지직", "탑툰", "조아라",
    "정부24", "고용24", "기상청 날씨누리", "국가통계포털 KOSIS",
    "학술연구정보서비스 RISS", "복지로", "한국장학재단",
    "국민건강보험공단", "국민연금공단", "국가건강정보포털", "건강보험심사평가원",
    "국민신문고", "한국소비자원", "국가전자도서관", "위택스",
    "식품안전나라", "안전운전 통합민원",
    "표준국어대사전", "서울시 교통정보 TOPIS",
    "K-Startup 창업지원포털", "특허로", "기업마당",
    "KIPRIS 지식재산정보검색", "관세청 유니패스", "대한상공회의소 코참넷",
)


def korean_first_shortcuts(records):
    """Prominent navigation to actual registered Korean-oriented services."""
    by_name = {
        entry.get("name"): entry for entry in records
        if isinstance(entry, dict) and entry.get("name")
    }
    entries = []
    for name in KOREAN_FIRST_SEARCH_NAMES:
        record = by_name.get(name)
        if not record:
            raise RuntimeError("Korean shortcut is missing registered entry: " + name)
        entries.append(
            '<li><a href="/directory?q=' + quote(name, safe="") + '">'
            + escape(name) + '</a> · ' + escape(record["category"]) + '</li>'
        )
    return (
        '<section class="lw-safety-note korean-first-shortcuts" '
        'aria-label="국내 사이트 먼저 찾기">'
        '<h2>국내 사이트 먼저 찾기</h2>'
        '<p>한국어 이용자가 자주 찾는 용도별 국내 서비스의 등록 예시입니다. '
        '목록 순서는 인기·안전 등급이 아니며, 접속 전 공식 운영 주체와 이용 조건을 확인하세요.</p>'
        '<ul>' + ''.join(entries) + '</ul>'
        '</section>'
    )


HOME_SEARCH_GUIDES = (
    ("seo-20261111-address-directory-search-examples", "주소모음 검색 방법",
     "사이트 이름과 도메인을 이용해 찾는 순서를 확인하세요."),
    ("seo-20261111-links-sites-comparison-checklist", "링크모음 비교 기준",
     "여러 사이트를 이용 목적과 조건에 따라 비교하세요."),
    ("seo-20261111-address-directory-no-results", "검색 결과가 없을 때",
     "등록 목록에서 원하는 사이트를 찾지 못했을 때 확인할 항목입니다."),
    ("seo-20261111-site-directory-selection-by-purpose", "사이트모음 이용 목적별 선택",
     "검색·커뮤니티·AI·스포츠 서비스를 용도별로 구분합니다."),
    ("seo-20261111-mobile-address-directory-check", "모바일에서 주소 확인",
     "휴대전화에서 실제 도메인을 확인하는 순서입니다."),
)


def homepage_search_guide_links(posts_root=POSTS):
    """Give Google's already-indexed homepage direct links to real useful guides.

    This supplements directory and blog navigation; no thin doorway pages,
    invented popularity claims, external links, or duplicate article content.
    """
    items = []
    for slug, label, explanation in HOME_SEARCH_GUIDES:
        article = posts_root / (slug + ".md")
        if not article.is_file() or not article.read_text(encoding="utf-8").startswith("# "):
            raise RuntimeError("Missing published homepage search guide: " + slug)
        items.append(
            '<li><a href="/blog/' + escape(slug, quote=True) + '/">'
            + escape(label) + '</a><p>' + escape(explanation) + '</p></li>'
        )
    return (
        '<section class="wrap seo-related-links seo-home-search-guides" '
        'aria-label="주소모음과 링크모음 이용 가이드">'
        '<h2>사이트를 찾을 때 필요한 이용 가이드</h2>'
        '<p>전체 목록에서 검색한 뒤 필요한 경우 다음 안내를 살펴보세요. '
        '이 글들은 실시간 접속 여부나 사이트 신뢰도를 보증하지 않습니다.</p>'
        '<ul>' + ''.join(items) + '</ul>'
        '</section>'
    )


def quick_service_searches(records, *, collapsed=False):
    """Task labels open real directory searches without typing."""
    registered = {item["name"] for item in records}
    tasks = (
        ("증명서 발급", "정부24"),
        ("국세 신고", "국세청 홈택스"),
        ("일자리 검색", "고용24"),
        ("프로야구 일정", "KBO 공식 홈페이지"),
        ("웹툰 보기", "네이버 웹툰"),
    )
    navigation = (
        '<nav class="lw-guide-nav" aria-label="업무별 사이트 검색">'
        + ''.join(
            f'<a href="/directory?q={quote(name, safe="")}">{label} · {escape(name)}</a>'
            for label, name in tasks if name in registered
        )
        + '</nav>'
    )
    if collapsed:
        return '<details><summary>업무별 사이트 검색</summary>' + navigation + '</details>'
    return navigation


def homepage_task_paths(records):
    """Match broad directory-search intent with real multi-category tasks."""
    by_name = {
        item.get("name"): item for item in records
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    sample = "네이버 웹툰"
    if sample not in by_name or by_name[sample].get("category") != "만화·웹툰":
        raise RuntimeError("Homepage task path is not backed by a registered webtoon service")
    url = "/directory?q=" + quote(sample, safe="")
    return (
        '<section class="wrap blog-home seo-home-task-paths" '
        'aria-label="사이트 이름과 이용 목적별 찾기">'
        '<div class="v47-section-heading"><h2>찾는 사이트에 따라 선택하세요</h2></div>'
        '<div class="blog-grid">'
        '<a class="blog-card" href="' + escape(url, quote=True) + '">'
        '<strong>사이트 이름이나 도메인을 알고 있을 때</strong>'
        '<span>예: 네이버 웹툰. 이름·도메인을 입력해 실제 등록된 주소와 설명을 확인합니다.</span>'
        '<span class="blog-card-more">등록 사이트 이름으로 검색 →</span></a>'
        '<a class="blog-card" href="/categories/">'
        '<strong>어떤 사이트를 쓸지 비교하고 싶을 때</strong>'
        '<span>커뮤니티·웹툰·AI 도구·스포츠·영상·검색·한인 생활 등 분야별 링크를 비교합니다.</span>'
        '<span class="blog-card-more">분야별 링크모음 살펴보기 →</span></a>'
        '<a class="blog-card" href="/guides/address-check">'
        '<strong>이동할 주소를 확인하고 싶을 때</strong>'
        '<span>등록 도메인과 실제 운영기관 안내를 대조하고 로그인 전에 주소를 확인합니다.</span>'
        '<span class="blog-card-more">사이트 주소 확인 방법 →</span></a>'
        '</div></section>'
    )


def directory_card_anchor(record):
    """Stable on-page anchor; no separate indexable thin page per listing."""
    url = record.get("anchor_url", record.get("url")) if isinstance(record, dict) else None
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError("Directory anchor requires a real current or previous HTTPS address")
    return "site-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:14]


def render_directory_catalog_cards(records):
    """Render crawlable cards directly from the verified catalog."""
    if not isinstance(records, list) or len(records) < 200:
        raise RuntimeError("Verified directory catalog unexpectedly empty")
    cards = []
    seen = set()
    for item in records:
        if not isinstance(item, dict):
            raise RuntimeError("Directory entry is not an object")
        name, category, description, url = (
            item.get("name"), item.get("category"),
            item.get("description"), item.get("url"))
        if any(not isinstance(value, str) or not value.strip()
               for value in (name, category, description, url)):
            raise RuntimeError("Directory entry missing required text")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise RuntimeError("Directory entry must use an HTTPS host: " + name)
        if url in seen:
            raise RuntimeError("Duplicate directory URL: " + url)
        seen.add(url)
        cards.append(
            '<article class="v6-card" id="' + directory_card_anchor(item) + '"><small>' + escape(category) +
            '</small><h3>' + escape(name) + '</h3><p>' + escape(description) +
            '</p><span class="site-domain">' + escape(parsed.hostname) + '</span>' +
            '<a aria-label="' + escape(name, quote=True) +
            ' 사이트 새 창에서 열기" href="' + escape(url, quote=True) +
            '" rel="noopener noreferrer external" target="_blank">사이트 방문 ↗</a>'
            '</article>'
        )
    return "".join(cards)


def replace_directory_catalog_cards(html, records):
    """Keep published static cards synchronized with the verified catalog."""
    pattern = re.compile(
        r'(?P<open><div class="v6-grid" id="v6-results">)'
        r'(?P<cards>.*?)'
        r'(?P<close></div>)', re.S)
    if len(pattern.findall(html)) != 1:
        raise RuntimeError("Directory static list container changed")
    rendered = render_directory_catalog_cards(records)
    return pattern.sub(
        lambda match: match.group("open") + rendered + match.group("close"),
        html, count=1)


def sync_category_card_copy(html, records, category):
    """Preserve each category layout while deriving descriptions from one source."""
    selected = [item for item in records if item.get("category") == category]
    # Standard category templates use a single `div.items`. Render its entire
    # list from the same catalog as /directory so verified additions can't
    # silently vanish from individual category pages.
    if html.count('<div class="items">') == 1:
        if not selected:
            raise RuntimeError("No published category items: " + category)
        cards = []
        for item in selected:
            name, description, url = item["name"], item["description"], item["url"]
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise RuntimeError("Invalid category listing URL: " + name)
            cards.append(
                '<article class="item" data-search="' +
                escape(name + " " + category + " " + description, quote=True) +
                '"><strong>' + escape(name) + '</strong><small>' +
                escape(category) + '</small><p>' + escape(description) +
                '</p><span class="site-domain">' + escape(parsed.hostname) +
                '</span><a aria-label="' + escape(name, quote=True) +
                ' 사이트 새 창에서 열기" href="' + escape(url, quote=True) +
                '" rel="noopener noreferrer external" target="_blank">사이트 방문</a></article>'
            )
        html, replaced = re.subn(
            r'<div class="items">.*?</div>',
            lambda _: '<div class="items">' + ''.join(cards) + '</div>',
            html, count=1, flags=re.S)
        if replaced != 1:
            raise RuntimeError("Category item container malformed: " + category)
        html = re.sub(r'\b\d+개(?=\s+사이트 안내)',
                      lambda _: str(len(selected)) + "개", html)
        return html
    pattern = re.compile(
        r'<article class="(?:item|v6-card)"[^>]*>.*?</article>', re.S)
    index = 0

    def update(match):
        nonlocal index
        if index >= len(selected):
            raise RuntimeError("Category has extra rendered cards: " + category)
        card = match.group(0)
        item = selected[index]
        index += 1
        links = re.findall(r'<a\b[^>]*href="(https://[^"]+)"', card)
        if len(links) != 1 or unescape(links[0]) != item["url"]:
            raise RuntimeError("Category card URL or order differs from catalog: " + category)
        paragraph = re.compile(r'<p>.*?</p>', re.S)
        card, count = paragraph.subn('<p>' + escape(item["description"]) + '</p>',
                                    card, count=1)
        if count != 1:
            raise RuntimeError("Category card has no description: " + item["name"])
        if card.startswith('<article class="item"'):
            data_search = escape(
                item["name"] + " " + category + " " + item["description"], quote=True)
            card, matches = re.subn(
                r'data-search="[^"]*"', lambda _: 'data-search="' + data_search + '"',
                card, count=1)
            if matches != 1:
                raise RuntimeError("Category search attribute missing: " + item["name"])
        return card

    html = pattern.sub(update, html)
    if index != len(selected):
        raise RuntimeError("Category has missing rendered cards: " + category)
    return html


def fingerprint_directory_scripts(html, assets_dir):
    """Version public directory scripts by their actual bytes, not hand-edited dates.

    This changes URLs only when a script changes, preserving CDN caching and
    avoiding stale browser search code after deployment.
    """
    filenames = ("directory-search.js", "directory.js", "mobile-menu.js",
                 "address-inspector.js", "site-comparison.js")
    for filename in filenames:
        script = assets_dir / filename
        if not script.is_file():
            raise RuntimeError("Missing directory browser asset: " + filename)
        digest = hashlib.sha256(script.read_bytes()).hexdigest()[:12]
        pattern = re.compile(
            r'(?P<start>src=")(?P<path>/?assets/' + re.escape(filename) +
            r')(?:\?[^"]*)?(?P<end>")'
        )
        html, count = pattern.subn(
            lambda match: match.group("start") + match.group("path") +
            "?v=" + digest + match.group("end"), html,
        )
        if count != 1:
            raise RuntimeError(
                f"Expected one directory script reference for {filename}; found {count}")
    return html


def directory_quick_comparison(records, categories):
    """Compact above-the-fold category summary backed by the published catalog.

    This helps a visitor choose a category without reading 211 static cards.
    No invented popularity, ratings, availability, or separate duplicate landing URLs.
    """
    if not isinstance(records, list) or not records:
        raise RuntimeError("Directory quick comparison requires real records")
    sections = []
    for category, slug, _, purpose in categories:
        matches = [item for item in records if item.get("category") == category]
        if not matches:
            raise RuntimeError(f"Missing active category in directory comparison: {slug}")
        names = [item["name"] for item in matches[:2]]
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise RuntimeError(f"Invalid published category examples: {slug}")
        direct_links = ' · '.join(
            '<a href="#' + directory_card_anchor(item) + '">'
            + escape(item["name"]) + '</a>'
            for item in matches[:2]
        )
        sections.append(
            '<li><a href="/categories/' + escape(slug, quote=True) + '">'
            + escape(category) + ' ' + str(len(matches)) + '개</a>'
            '<span> · ' + direct_links + '</span>'
            '<p>' + escape(purpose) + '</p></li>'
        )
    if len(sections) != len(categories):
        raise RuntimeError("Directory comparison navigation incomplete")
    return (
        '<section id="directory-quick-compare" class="lw-safety-note seo-category-quick-compare" '
        'aria-label="사이트모음 분야별 등록 개수와 예시">'
        '<h2>사이트모음 분야별 한눈에 비교</h2>'
        '<p>목적에 맞는 링크모음 분야를 먼저 선택하세요. 각 분야의 등록 개수와 '
        '실제 목록에 있는 사이트 두 곳을 보여줍니다. 개수는 이용자 수나 추천 순위가 아닙니다.</p>'
        '<ul>' + ''.join(sections) + '</ul>'
        '<p><a href="/directory">주소모음 전체 목록 검색</a> · '
        '<a href="/guides/choose-directory">분야별 링크 선택 기준</a></p>'
        '</section>'
    )


def directory_task_paths(records):
    """Helpful canonical search links derived from existing catalog records."""
    existing = {entry.get("name") for entry in records if isinstance(entry, dict)}
    tasks = (
        ("민원 접수와 증명서 발급",
         "국민신문고", "정부24",
         "민원·제안 접수와 정부 증명서 발급은 서로 다른 업무입니다."),
        ("특허·상표 자료 검색과 출원",
         "KIPRIS 지식재산정보검색", "특허로",
         "공개 지식재산 정보 탐색과 실제 전자출원 절차를 구분하세요."),
        ("창업지원과 중소기업 지원",
         "K-Startup 창업지원포털", "기업마당",
         "창업 단계별 공고와 일반 중소기업 정책지원 공고를 비교하세요."),
        ("국세 신고와 지방세 납부",
         "국세청 홈택스", "위택스",
         "국세와 지방세의 담당 기관을 구분해 실제 납부 경로를 찾으세요."),
        ("건강보험과 국민연금 업무",
         "국민건강보험공단", "국민연금공단",
         "보험 자격·보험료 확인과 연금 가입·수급 안내를 구분하세요."),
        ("취업 지원과 학자금 지원",
         "고용24", "한국장학재단",
         "구직 관련 제도와 대학 학자금 지원의 신청 조건을 따로 확인하세요."),
        ("날씨와 도시 교통정보",
         "기상청 날씨누리", "서울시 교통정보 TOPIS",
         "전국 날씨 예보와 서울 도로 소통·통제 안내를 목적에 맞게 확인하세요."),
        ("도로명주소 조회와 등기사항 확인",
         "주소정보누리집 도로명주소", "대법원 인터넷등기소",
         "도로명주소·우편번호를 찾는 일과 부동산·법인 등기사항을 확인하는 업무는 다릅니다."),
        ("경제지표와 범분야 공식 통계",
         "한국은행 경제통계시스템 ECOS", "국가통계포털 KOSIS",
         "금리·물가·통화 통계는 한국은행 ECOS에서, 인구·사회 분야는 KOSIS에서 찾아보세요."),
        ("사이버범죄 신고와 일반 민원",
         "경찰청 사이버범죄 신고시스템 ECRM", "국민신문고",
         "온라인 사기 등 수사 대상 피해 신고와 행정기관 민원·제안 접수를 구분하세요."),
        ("전자소송과 법령 원문 확인",
         "대한민국 법원 전자소송포털", "국가법령정보센터",
         "소송 서류 제출과 사건 관리는 전자소송포털, 법률·시행령 원문 검색은 국가법령정보센터에서 진행합니다."),
        ("교수학습 자료와 고교강의",
         "에듀넷 티클리어", "EBSi 고교강의",
         "학교 교육과정·교수학습 자료와 고교 온라인 강의의 이용 목적을 구분해 찾으세요."),
    )
    output = []
    for label, first, second, description in tasks:
        if first not in existing or second not in existing:
            raise RuntimeError(f"Directory task guide missing registered service: {first}/{second}")
        links = (
            '<a href="/directory?q=' + quote(first, safe="") + '">' + escape(first) + '</a>',
            '<a href="/directory?q=' + quote(second, safe="") + '">' + escape(second) + '</a>',
        )
        output.append(
            '<li><strong>' + escape(label) + '</strong> — ' + escape(description)
            + ' ' + links[0] + ' · ' + links[1] + '</li>'
        )
    return (
        '<section id="directory-task-paths" class="lw-safety-note seo-task-paths" '
        'aria-label="국내 공공 서비스 업무별 빠른 찾기">'
        '<h2>국내 사이트모음, 실제 업무로 찾기</h2>'
        '<p>사이트 이름이 헷갈린다면 해야 할 일을 먼저 구분하세요. '
        '아래 링크는 현재 등록 목록의 검색 결과로 연결됩니다. '
        '서비스의 접수 상태나 자격을 보증하지는 않습니다.</p>'
        '<ul>' + ''.join(output) + '</ul>'
        '<p><a href="/categories/search">국내 공공 서비스 전체 비교하기</a> · '
        '<a href="/guides/address-check">공식 주소 확인 방법</a></p>'
        '</section>'
    )




def directory_address_correction_request(records):
    """Visible human correction path, with no fabricated verification or backend.

    Registered directory data is read-only in the static SEO deployment.
    Readers can supply a precise, source-backed correction request through
    the existing public editorial contact on the About page.
    """
    if not isinstance(records, list) or len(records) < 2:
        raise RuntimeError("Address correction guidance needs the real catalog")
    return (
        '<section id="directory-correction-request" '
        'class="lw-safety-note seo-directory-corrections" '
        'aria-labelledby="directory-correction-heading">'
        '<h2 id="directory-correction-heading">주소가 바뀌었거나 설명이 틀렸나요?</h2>'
        '<p>현재 등록된 사이트 주소가 이동했거나 연결되지 않는다면 알려주세요. '
        '목록의 등록 상태는 실시간 접속 확인이나 공식 인증을 뜻하지 않습니다. '
        '제보는 검토한 뒤 필요한 경우에만 반영합니다.</p>'
        '<ol><li>사이트 이름과 링크위키에 표시된 주소를 적습니다.</li>'
        '<li>변경된 공식 주소가 있다면 운영기관의 공지·공식 페이지 근거를 첨부합니다.</li>'
        '<li>문제 종류(연결 오류·이동·설명 오류)와 확인 날짜를 적습니다.</li></ol>'
        '<p><a href="https://t.me/linkwiki_info" rel="noopener noreferrer external" '
        'target="_blank">등록 주소 오류 제보하기 (텔레그램)</a> · '
        '<a href="/about">목록 관리·검증 범위 보기</a></p>'
        '<p>비밀번호·인증번호·결제정보 등 민감한 내용은 보내지 마세요. '
        '제보만으로 링크가 자동 변경되거나 안전하다고 표시되지 않습니다.</p>'
        '</section>'
    )


def directory_two_site_comparison(records):
    """Interactive, local-only comparison backed by the existing static cards.

    This panel adds a real user task to the canonical directory page, rather
    than creating templated doorway pages for individual site pairs.
    """
    if not isinstance(records, list) or len(records) < 2:
        raise RuntimeError("Two-site comparison requires real catalog records")
    return (
        '<section id="directory-two-site-compare" '
        'class="lw-safety-note lw-site-compare" '
        'aria-labelledby="site-compare-heading">'
        '<h2 id="site-compare-heading">사이트모음에서 두 서비스 직접 비교</h2>'
        '<p>검색 결과에서 비교에 담기를 두 번 누르거나 아래에서 두 사이트를 고르세요. '
        '분야·도메인·설명을 나란히 볼 수 있습니다. 등록 정보만 이용하며 외부로 데이터를 보내지 않습니다.</p>'
        '<form id="lw-site-compare-form">'
        '<label for="lw-site-compare-first">첫 번째 사이트</label>'
        '<select id="lw-site-compare-first" required>'
        '<option value="">자바스크립트로 등록 목록을 불러옵니다</option></select>'
        '<label for="lw-site-compare-second">두 번째 사이트</label>'
        '<select id="lw-site-compare-second" required>'
        '<option value="">자바스크립트로 등록 목록을 불러옵니다</option></select>'
        '<button type="submit">두 사이트 비교하기</button>'
        '</form>'
        '<div id="lw-site-compare-result" role="status" aria-live="polite">'
        '<p>두 사이트의 차이를 확인하려면 목록에서 각각 선택하세요.</p></div>'
        '<p>실제 이용 조건은 바뀔 수 있습니다. '
        '<a href="/guides/address-check">공식 주소 확인 방법</a>을 함께 참고하세요.</p>'
        '</section>'
    )


def directory_everyday_task_paths(records):
    """Let visitors compare real registered services by everyday user intent.

    Each pair represents two genuine catalog entries, not a popularity claim
    or a fabricated ranking. The deep links reuse the canonical search page.
    """
    if not isinstance(records, list) or not records:
        raise RuntimeError("Everyday directory tasks require verified records")
    names = {row.get("name") for row in records if isinstance(row, dict)}
    tasks = (
        ("장소 찾기와 길찾기", "네이버 지도", "카카오맵",
         "대중교통·도보 경로를 비교할 때 출발지와 실제 운영 시간을 확인하세요."),
        ("문서 작성과 번역", "ChatGPT", "DeepL",
         "아이디어·초안 작성과 언어 번역은 다른 작업입니다. 중요한 내용은 원문을 대조하세요."),
        ("이미지·발표 자료 디자인", "Canva", "미리캔버스",
         "템플릿의 제공 범위, 내보내기 형식과 라이선스 조건을 확인하세요."),
        ("지역 중고 거래와 게시판 거래", "당근", "중고나라",
         "거래 지역·판매자 신원·물품 상태와 결제 조건을 따로 점검하세요."),
        ("동영상 검색과 구독형 시청", "유튜브", "넷플릭스",
         "개별 영상 검색과 구독형 콘텐츠 이용은 제공 방식과 비용이 다릅니다."),
        ("웹툰 플랫폼 선택", "네이버 웹툰", "카카오웹툰",
         "연재 작품, 무료 공개 범위와 유료 회차 조건을 비교하세요."),
        ("뉴스 자료와 공식 통계", "빅카인즈", "국가통계포털 KOSIS",
         "뉴스 기사 분석과 국가 통계 조회는 자료 성격과 기준 시점이 다릅니다."),
    )
    cards = []
    seen = set()
    for label, first, second, advice in tasks:
        if first == second or first not in names or second not in names:
            raise RuntimeError(f"Everyday task missing real catalog entries: {first}/{second}")
        if label in seen:
            raise RuntimeError(f"Duplicate everyday task: {label}")
        seen.add(label)
        cards.append(
            '<li><strong>' + escape(label) + '</strong> — ' + escape(advice)
            + ' <a href="/directory?q=' + quote(first, safe="") + '">'
            + escape(first) + '</a> · <a href="/directory?q='
            + quote(second, safe="") + '">' + escape(second) + '</a></li>'
        )
    return (
        '<section id="directory-everyday-tasks" '
        'class="lw-safety-note seo-everyday-tasks" '
        'aria-label="생활 목적별 사이트 비교">'
        '<h2>생활 목적별 링크모음·사이트모음 선택</h2>'
        '<p>검색어가 떠오르지 않을 때 필요한 작업부터 고르세요. '
        '아래 사이트들은 실제 등록 목록의 비교 예시이며 인기 순위, '
        '공식 인증 또는 현재 연결 상태를 의미하지 않습니다.</p>'
        '<ul>' + ''.join(cards) + '</ul>'
        '<p><a href="/directory">주소모음 전체 검색</a> · '
        '<a href="/categories/">분야별 사이트 목록</a></p></section>'
    )


def directory_search_help(records, categories):
    """Helpful, static, data-backed search instructions for directory visitors."""
    if not records or not categories:
        raise RuntimeError("Directory guidance needs published categories")
    counts = {
        category: sum(1 for item in records if item.get("category") == category)
        for category, _, _, _ in categories
    }
    active = [(category, slug) for category, slug, _, _ in categories if counts[category]]
    if not active:
        raise RuntimeError("No directory categories available")
    # Demonstrate the real search URL using data-backed registered examples.
    # No invented recommendations, rankings or uptime claims.
    samples = []
    for category in ("검색·포털", "AI 도구", "스포츠"):
        selected = next(
            (entry for entry in records
             if entry.get("category") == category
             and isinstance(entry.get("name"), str)
             and entry["name"].strip()), None)
        if selected:
            name = selected["name"].strip()
            samples.append(
                '<li><a href="/directory?q=' + quote(name, safe="") + '">'
                + escape(name) + ' 이름으로 검색하기</a> · '
                + escape(category) + ' 등록 항목</li>'
            )
    domain_samples = []
    for category in ("검색·포털", "AI 도구"):
        selected = next(
            (entry for entry in records
             if entry.get("category") == category
             and isinstance(entry.get("url"), str)
             and urlparse(entry["url"]).scheme == "https"
             and urlparse(entry["url"]).hostname), None)
        if selected:
            hostname = urlparse(selected["url"]).hostname
            domain_samples.append(
                '<li><a href="/directory?q=' + quote(hostname, safe="") + '">'
                + escape(hostname) + ' 도메인으로 검색하기</a> · '
                + escape(category) + ' 등록 항목</li>'
            )
    example_section = (
        '<div class="lw-search-examples"><h3>실제 등록 사이트 검색 예시</h3>'
        '<p>항목을 선택하면 검색어가 입력된 전체 목록으로 이동합니다. '
        '예시는 인기 순위나 실시간 접속 확인 결과가 아닙니다.</p>'
        '<ul>' + ''.join(samples + domain_samples) + '</ul></div>'
        if samples or domain_samples else ''
    )
    return (
        '<section id="site-list-guide" class="lw-safety-note seo-search-help" aria-label="사이트모음 검색 및 확인 방법">'
        '<h2>주소모음·링크모음 검색 사용 방법</h2>'
        '<ol>'
        '<li>찾는 사이트 이름이나 도메인을 알고 있으면 위 검색창에 입력합니다. '
        '주소 전체(예: https://www.naver.com/)를 붙여넣으면 해당 도메인과 경로가 '
        '등록된 항목을 찾을 수 있습니다. '
        '여러 단어를 함께 입력하면 해당 조건을 충족하는 목록으로 좁혀집니다.</li>'
        '<li>목적만 알고 있으면 분야 선택 버튼 또는 아래 카테고리 링크로 이동합니다. '
        f'현재 {len(active)}개 분야에 {len(records)}개 사이트가 등록되어 있습니다.</li>'
        '<li>목록의 설명과 등록 도메인을 비교한 뒤 방문합니다. '
        '외부 사이트의 공식 인증이나 실시간 접속 가능 여부는 보증하지 않습니다. '
        '두 목록 사이에서 선택이 어렵다면 '
        '<a href="/guides/directory-comparison">사이트 목록 비교 기준</a>을 참고하세요.</li>'
        '</ol>'
        + example_section +
        '<h3>자주 묻는 질문</h3>'
        '<h4>사이트 이름을 몰라도 주소모음에서 찾을 수 있나요?</h4>'
        '<p>네. 커뮤니티, AI 도구, 스포츠 등 용도나 분야별로 목록을 좁힐 수 있습니다. '
        '<a href="/categories/">분야별 사이트모음</a>에서 등록된 분야를 확인하세요.</p>'
        '<h4>링크모음의 사이트 주소는 모두 공식 주소인가요?</h4>'
        '<p>아닙니다. 이 목록은 탐색용 등록 정보이며 운영 주체를 인증하지 않습니다. '
        '<a href="/guides/address-check">공식 주소 확인 방법</a>에 따라 '
        '방문 전 서비스 공지와 실제 주소를 대조하세요.</p>'
        '<h4>복사한 사이트 주소 전체를 검색할 수 있나요?</h4>'
        '<p>네. HTTPS 주소 전체를 검색창에 붙여넣으면 등록된 도메인과 경로를 기준으로 '
        '목록을 확인할 수 있습니다. 링크위키 목록에 없다는 사실이 해당 사이트의 '
        '안전성이나 실제 운영 상태를 뜻하지는 않습니다.</p>'
        '<h4>사이트모음에서 검색한 링크가 열리지 않으면 어떻게 하나요?</h4>'
        '<p>주소를 다시 확인하고 공식 운영 채널의 변경 공지를 살펴보세요. '
        '<a href="/guides/link-troubleshooting">접속 오류 안내</a>도 참고할 수 있습니다.</p>'
        '</section>'
    )


def directory_address_inspector():
    """One useful, no-network URL anatomy checker on the canonical listing page."""
    return (
        '<section id="address-inspector" class="lw-safety-note seo-address-inspector" '
        'aria-label="웹사이트 주소 실제 도메인 확인">'
        '<h2>주소모음에서 찾은 주소의 실제 도메인 확인</h2>'
        '<p>링크를 클릭하기 전에 주소를 붙여넣고 접속 대상 호스트를 확인하세요. '
        '입력한 주소는 서버로 전송하지 않으며 외부 사이트에도 접속하지 않습니다. '
        '공식 운영 여부·안전성·현재 접속 가능 상태는 판정하지 않습니다.</p>'
        '<form id="lw-address-form" class="v6-search" role="search">'
        '<label for="lw-address-input">확인할 전체 주소</label>'
        '<input id="lw-address-input" type="url" required maxlength="2048" '
        'placeholder="https://example.com.login-check.test/account" '
        'autocomplete="off" spellcheck="false">'
        '<button type="submit">실제 도메인 확인</button></form>'
        '<div id="lw-address-result" role="status" aria-live="polite"></div>'
        '<p>주소에 익숙한 사이트명이 포함되어 있어도 그것이 실제 접속 도메인과 '
        '같다는 뜻은 아닙니다. 로그인이나 결제 전에는 운영자의 공식 공지에서 '
        '실제 도메인을 별도로 대조하세요. '
        '<a href="/guides/address-check">공식 주소 확인 순서</a></p>'
        '</section>'
    )


def directory_collection_schema(records, categories):
    """Truthful CollectionPage and eight category navigation entries.

    Uses published same-site categories rather than claiming that external
    destinations are officially endorsed, reviewed or ranked.
    """
    counts = {}
    for record in records:
        if isinstance(record, dict):
            category = record.get("category")
            if isinstance(category, str):
                counts[category] = counts.get(category, 0) + 1
    active = [
        (slug, heading) for category, slug, heading, _ in categories
        if counts.get(category, 0)
    ]
    items = [
        {
            "@type": "ListItem", "position": index + 1,
            "name": heading,
            "url": SITE + "/categories/" + slug,
        }
        for index, (slug, heading) in enumerate(active)
    ]
    if not items:
        raise RuntimeError("Cannot build category schema without listed sites")
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": SITE + "/directory#collection",
        "url": SITE + "/directory",
        "name": "주소모음·링크모음·사이트모음 통합 검색",
        "inLanguage": "ko",
        "mainEntity": {
            "@type": "ItemList",
            "name": "링크위키 분야별 등록 사이트",
            "numberOfItems": len(items),
            "itemListElement": items,
        },
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + payload.replace("</", "<\\/") + '</script>'


def directory_category_overview(records, categories, per_category=3):
    """Make practical comparisons from exact published listing metadata.

    Descriptions come from the directory source, not speculative rankings or
    claims about current uptime, pricing or official affiliations.
    """
    sections = []
    for category, slug, heading, purpose in categories:
        matching = [entry for entry in records
                    if isinstance(entry, dict) and entry.get("category") == category]
        examples = [
            entry for entry in matching
            if isinstance(entry.get("name"), str) and entry["name"].strip()
            and isinstance(entry.get("description"), str)
            and entry["description"].strip()
        ][:per_category]
        if not examples:
            continue
        listing = ''.join(
            '<li><strong>' + escape(entry["name"].strip()) + '</strong>'
            + ' (등록 도메인: ' + escape(urlparse(entry["url"]).hostname or "") + ')</li>'
            for entry in examples
        )
        sections.append(
            '<section class="seo-directory-category">'
            f'<h3><a href="/categories/{escape(slug, quote=True)}">{escape(heading)}</a></h3>'
            f'<p>{escape(purpose)}</p>'
            f'<p>등록 사이트 {len(matching)}개 · 아래는 등록 목록의 예시입니다.</p>'
            '<ul>' + listing + '</ul>'
            f'<p><a href="/categories/{escape(slug, quote=True)}">'
            '이 분야 전체 등록 사이트 보기</a></p>'
            '</section>'
        )
    return (
        '<section id="site-category-comparison" class="lw-safety-note seo-directory-overview" '
        'aria-label="분야별 사이트 목록 비교">'
        '<h2>분야별 사이트모음 비교 및 선택</h2>'
        '<p>아래는 분야별 용도, 등록 사이트 이름과 도메인을 한눈에 비교하도록 정리한 예시입니다. '
        '각 사이트의 자세한 설명과 검색 기능은 위의 전체 목록 및 개별 분야 페이지에서 확인하세요. '
        '서비스의 공식 인증·현재 접속 상태·요금·안전성을 보증하지 않습니다.</p>'
        + ''.join(sections)
        + '</section>'
    )


def article_category_links(title, categories):
    """Link each guide only to existing, topically related directory categories."""
    valid = {"/categories/" + slug for _, slug, _, _ in CATEGORY_LANDING}
    output = []
    for label, url in categories:
        if url in valid and (label, url) not in output:
            output.append((label, url))
    return ''.join(
        '<a href="' + escape(url, quote=True) + '">' +
        escape(label) + ' 사이트 목록</a>'
        for label, url in output[:2]
    )


def category_article_links(posts, slug, limit=5):
    """Preserve essential reference guides while mixing newer topical guides.

    Links must still come from published post records, never invented slugs.
    """
    from seo.auto_seo import related_categories
    pins = {
        "search": (
            "/blog/seo-20261030-26325b73af/",
            "/blog/seo-20261110-korean-education-sites-guide/",
        ),
        "ai": ("/blog/seo-20261110-korean-ai-tools-by-task-guide/",),
    }
    selected = []
    seen = set()
    relevant = [
        post for post in posts
        if any(url == f"/categories/{slug}" for _, url in related_categories(post["title"]))
    ]
    for pinned in pins.get(slug, ()):
        chosen = next((post for post in relevant if post["url"] == pinned), None)
        if chosen is not None and len(selected) < limit:
            selected.append(chosen)
            seen.add(pinned)
    for post in relevant:
        if post["url"] not in seen and len(selected) < limit:
            selected.append(post)
            seen.add(post["url"])
    return selected


def add_editorial_related_articles(posts, max_links=3):
    """Cross-link only guide articles sharing a real category intent.

    Select the newest matching guides in stable order. Do not invent links or
    add generic keyword blocks to articles without an actual match.
    """
    from seo.auto_seo import related_categories
    if not 1 <= max_links <= 5:
        raise ValueError("Invalid related article limit")
    result = {}
    for current in posts:
        current_categories = {url for _, url in related_categories(current["title"])}
        if not current_categories:
            continue
        candidates = []
        for other in posts:
            if other["url"] == current["url"]:
                continue
            overlap = current_categories.intersection(
                {url for _, url in related_categories(other["title"])}
            )
            if overlap:
                candidates.append((len(overlap), other))
        candidates.sort(key=lambda item: (-item[0], item[1]["url"]))
        if not candidates:
            continue
        links = candidates[:max_links]
        result[current["url"]] = (
            '<section class="blog-related" aria-label="관련 사이트 이용 가이드">'
            '<h2>관련 사이트 이용 가이드</h2><ul>'
            + ''.join(
                f'<li><a href="{escape(post["url"], quote=True)}">'
                f'{escape(post["title"])}</a></li>'
                for _, post in links)
            + '</ul></section>'
        )
    return result


# Only these source paths are meant to be served to the public. In
# particular, Cloudflare runs npm install for Playwright in CI; copying all
# root folders would publish node_modules and make its internal HTML pages
# fail our sitemap/canonical SEO audit (and expose unnecessary code).
PUBLIC_SOURCE_DIRS = ("assets", "categories", "guides")
PUBLIC_SOURCE_FILES = (
    "404.html", "_headers", "_redirects", "about.html", "directory.html",
    "favicon.ico", "favicon.png", "index.html",
    "naver8cd598bf6fee0ad116a386a3d915bb9f.html",
    "privacy.html", "robots.txt", "sitemap.xml", "sitemap-v2.xml",
)


def copy_public_sources(source_root, output_root):
    """Copy a positive allowlist so installed dependencies never become pages."""
    for name in PUBLIC_SOURCE_DIRS:
        source = source_root / name
        if not source.is_dir() or source.is_symlink():
            raise RuntimeError(f"Required public source directory missing or unsafe: {name}")
        shutil.copytree(source, output_root / name, symlinks=False)
    for name in PUBLIC_SOURCE_FILES:
        source = source_root / name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"Required public source file missing or unsafe: {name}")
        shutil.copy2(source, output_root / name)



def article_provenance(title, canonical, published_date, modified_date=None):
    """Describe editorial evidence without invented reviewers or testing."""
    markup = (
        '<aside class="blog-source-note" aria-label="글의 정보 근거">'
        '<h2>이 글의 정보 기준</h2>'
        '<p>발행: 링크위키. 서비스 이름·분야·주소 설명은 링크위키 공개 등록 목록을 '
        '바탕으로 정리했습니다. 글 작성 과정에는 자동화 도구가 활용될 수 있습니다. '
        '외부 사이트에 로그인하거나 결제하여 검증했다고 주장하지 않습니다.</p>'
        '<p>최신 서비스 기능과 운영 조건은 해당 운영기관에서 다시 확인하세요. '
        '<a href="/about">자료 작성·확인 원칙</a>에서 검증 범위와 오류 신고 방법을 볼 수 있습니다.</p>'
        '</aside>'
    )
    if not published_date:
        return markup, ""
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "datePublished": published_date,
        "author": {"@type": "Organization", "name": "링크위키", "url": SITE + "/about"},
        "publisher": {"@type": "Organization", "name": "링크위키", "url": SITE + "/"},
        "inLanguage": "ko",
    }
    if modified_date and modified_date > published_date:
        schema["dateModified"] = modified_date
    script = '<script type="application/ld+json">' + json.dumps(
        schema, ensure_ascii=False, separators=(",", ":")
    ).replace("<", "\\u003c") + '</script>'
    return markup, script


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    copy_public_sources(ROOT, OUT)
    for existing_page in OUT.rglob('*.html'):
        existing_html = existing_page.read_text(encoding='utf-8')
        improved_html = add_nav(existing_html)
        if improved_html != existing_html:
            existing_page.write_text(improved_html, encoding='utf-8')
    header, footer = chrome()
    significant_updates = json.loads(
        (ROOT / "seo" / "significant-page-updates.json").read_text(encoding="utf-8"))
    posts = []
    for source in sorted(POSTS.glob("*.md"), reverse=True) if POSTS.exists() else []:
        body = source.read_text(encoding="utf-8-sig")
        if not body.strip() or len(body.strip()) < 150:
            continue
        name = slug_for(source)
        title = extract_title(body)
        desc = excerpt(re.sub(r'^#.*$', '', body, count=1, flags=re.M))
        url = f"/blog/{quote(name)}/"
        canonical = SITE + url
        published_date = stable_post_lastmod(source)
        modified_date = significant_updates.get(url)
        display_date = published_date.replace("-", ".") if published_date else ""
        date_labels = (
            f'게시 <time datetime="{published_date}">{display_date}</time>'
            if published_date else ""
        )
        if published_date and modified_date and modified_date > published_date:
            modified_display = escape(modified_date.replace("-", "."))
            date_labels += f' · 수정 <time datetime="{escape(modified_date)}">{modified_display}</time>'
        content_body = re.sub(r'^#\s+.*(?:\n|$)', '', body, count=1)
        provenance, structured_article = article_provenance(
            title, canonical, published_date, modified_date)
        from seo.auto_seo import related_categories
        related_links = article_category_links(title, related_categories(title))
        article = (f'<div class="wrap blog-wrap"><nav class="blog-breadcrumb"><a href="/">홈</a> / '
                   f'<a href="/blog/">사이트 정보</a></nav><article class="blog-article">'
                   f'<p class="eyebrow">LINKWIKI · 사이트 정보</p><h1>{escape(title)}</h1>'
                   + (f'<p class="blog-date">{date_labels}</p>' if date_labels else '') +
                   f'<div class="blog-content">{markdown(content_body)}</div>'
                   + provenance +
                   '<div class="blog-bottom"><a href="/">주소모음·링크모음 홈</a>'
                   '<a href="/directory">전체 주소모음·사이트모음 검색</a>'
                   '<a href="/categories/">분야별 링크모음 보기</a>'
                   + related_links +
                   '<a href="/blog/">다른 이용 가이드 보기</a>'
                   '<a href="https://linkwiki01.com/" rel="noopener noreferrer">링크위키 바로가기</a></div></article></div>')
        target = OUT / "blog" / name / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        built_html = document(title, desc, canonical, article, header, footer)
        if structured_article:
            built_html = built_html.replace("</head>", structured_article + "</head>", 1)
        target.write_text(built_html, encoding="utf-8")
        posts.append({"title": title, "description": desc, "url": url, "date": display_date,
                      "published": published_date, "modified": modified_date or published_date})

    # Related articles add genuine crawlable paths between matching guides.
    # Construct after all posts are collected, without modifying Markdown.
    related_sections = add_editorial_related_articles(posts)
    for post in posts:
        section = related_sections.get(post["url"])
        if not section:
            continue
        slug = post["url"].strip("/").split("/")[-1]
        article_path = OUT / "blog" / slug / "index.html"
        html = article_path.read_text(encoding="utf-8")
        anchor = '<div class="blog-bottom">'
        if html.count(anchor) != 1:
            raise RuntimeError(f"Blog related links placement changed: {slug}")
        article_path.write_text(html.replace(anchor, section + anchor, 1), encoding="utf-8")

    def cards(entries):
        if not entries:
            return '<p class="blog-empty">새로운 이용 가이드를 준비하고 있습니다.</p>'
        return ''.join(f'<a class="blog-card" href="{escape(p["url"], quote=True)}">'
                       f'<span class="blog-card-label">사이트 정보{(" · " + p["date"]) if p["date"] else ""}</span>'
                       f'<strong>{escape(p["title"])}</strong><span>{escape(p["description"][:95])}</span>'
                       '<span class="blog-card-more">글 읽기 →</span></a>' for p in entries)

    listing = ('<div class="wrap blog-wrap"><nav class="blog-breadcrumb"><a href="/">홈</a> / 사이트 정보</nav>'
               '<div class="blog-heading"><p class="eyebrow">LINKWIKI · GUIDE JOURNAL</p>'
               '<h1>사이트 탐색 정보</h1><p>유용한 링크 탐색법과 주소 확인 방법을 정리합니다.</p></div>'
               f'<div class="blog-grid">{cards(posts)}</div></div>')
    blog_index = OUT / "blog" / "index.html"
    blog_index.parent.mkdir(parents=True, exist_ok=True)
    blog_index.write_text(document("사이트 탐색 정보", "링크모음과 주소모음 안전 이용 방법을 안내합니다.",
                                   SITE + "/blog/", listing, header, footer), encoding="utf-8")

    # A restrained homepage panel between the existing guide list and how-to section.
    home = polish_home_intent((OUT / "index.html").read_text(encoding="utf-8"))
    panel = ('<section class="wrap blog-home" aria-label="최근 등록된 정보">'
             '<div class="v47-section-heading"><h2>최근 등록된 정보</h2>'
             '<a href="/blog/">전체 글 보기 <span aria-hidden="true"></span></a></div>'
             f'<div class="blog-grid">{cards(posts[:3])}</div></section>')
    position = '<section aria-label="링크모음 이용 방법"'
    if position not in home:
        raise RuntimeError("기존 메인 구조가 달라져 게시판 삽입 위치를 확인할 수 없습니다")
    first_party_records = json.loads(
        (OUT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
    if not isinstance(first_party_records, list) or not first_party_records:
        raise RuntimeError("Directory data required for homepage search-intent guide")
    # Keep published homepage counts consistent with the verified directory data.
    # The source HTML preserves its editorial layout; only generated output changes.
    actual_count = len(first_party_records)
    home, count_replacements = re.subn(
        r"\b\d+개(?= 등록 (?:사이트|항목))",
        lambda match: f"{actual_count}개", home,
    )
    if count_replacements < 2:
        raise RuntimeError("Homepage directory count labels changed; review required")
    search_form_end = home.index("</form>", home.index('id="lw-home-query"')) + len("</form>")
    home = home[:search_form_end] + quick_service_searches(first_party_records) + home[search_form_end:]
    homepage_intents = core_search_intent_section(actual_count)
    real_directory_examples = homepage_directory_examples(first_party_records, CATEGORY_LANDING)
    home = home.replace(position, panel + homepage_task_paths(first_party_records) + homepage_intents + homepage_search_guide_links() + korean_first_shortcuts(first_party_records) + real_directory_examples + position, 1)
    home = home.replace('</head>', '<link href="/assets/blog.css" rel="stylesheet"/></head>', 1)
    (OUT / "index.html").write_text(home, encoding="utf-8")

    # One useful navigation hub backed by existing registered sites, not eight
    # duplicate keyword doorway pages. Individual category pages remain intact.
    records = json.loads((OUT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
    counts = {}
    for record in records:
        counts[record["category"]] = counts.get(record["category"], 0) + 1
    # Render all real directory categories as crawlable links on the primary
    # /directory landing page. The counts come from published directory data,
    # avoiding stale labels or navigation gaps as the dataset changes.
    directory_path = OUT / "directory.html"
    directory_html = directory_path.read_text(encoding="utf-8")
    directory_html = sync_directory_count(directory_html, len(records))
    directory_html = replace_directory_catalog_cards(directory_html, records)
    # Lead with search before the category and editorial shortcuts.
    search_form = re.compile(r'<form class="v6-search" id="v6-form".*?</form>', re.S)
    forms = search_form.findall(directory_html)
    if len(forms) != 1:
        raise RuntimeError("Directory search form missing or duplicated")
    directory_html = search_form.sub('', directory_html, count=1)
    directory_nav_pattern = (r'<nav aria-label="분야별 사이트모음 바로가기"'
                             r' class="lw-guide-nav">.*?</nav>')
    if len(re.findall(directory_nav_pattern, directory_html, flags=re.S)) != 1:
        raise RuntimeError("Directory category navigation changed; review required")
    directory_nav = (
        '<nav aria-label="분야별 사이트모음 바로가기" class="lw-guide-nav">'
        + ''.join(
            f'<a href="/categories/{slug}">{escape(category)} {counts[category]}개</a>'
            for category, slug, _, _ in CATEGORY_LANDING
            if counts.get(category, 0) > 0
        )
        + '<a href="/categories/">전체 분야 보기</a>'
        + '<a href="#site-list-guide">검색 이용 안내</a>'
        + '<a href="#site-category-comparison">분야별 등록 예시</a>'
        + '<a href="#site-purpose-comparison">목적별 선택법</a>'
        + '<a href="#directory-everyday-tasks">생활 목적별 비교</a>'
        + '<a href="#site-related-guides">관련 이용 가이드</a>'
        + '<a href="/guides/directory-maintenance">목록 관리 기록</a></nav>'
    )
    search_navigation = (
        '<nav aria-label="검색 도구 바로가기" class="lw-guide-nav">'
        '<a href="#v6-count">검색 결과로 이동</a>'
        '<a href="/categories/">분야별 사이트</a>'
        '<a href="#directory-two-site-compare">두 사이트 직접 비교</a>'
        '<a href="#directory-correction-request">주소 오류 제보</a>'
        '<a href="#site-related-guides">관련 이용 가이드</a></nav>'
    )
    directory_html = re.sub(
        directory_nav_pattern, lambda _: forms[0] + search_navigation + quick_service_searches(records, collapsed=True),
        directory_html, count=1, flags=re.S,
    )
    after_results = '<nav aria-label="관련 안내" class="lw-guide-nav">'
    if directory_html.count(after_results) != 1:
        raise RuntimeError("Directory related navigation changed; review required")
    directory_html = directory_html.replace(
        after_results,
        directory_nav
        + korean_first_shortcuts(records)
        + directory_quick_comparison(records, CATEGORY_LANDING)
        + directory_task_paths(records)
        + directory_two_site_comparison(records)
        + directory_address_correction_request(records)
        + after_results,
        1,
    )

    # Site descriptions are static and crawlable, not dependent on JavaScript.
    # Keep existing search/filter controls and every directory card unchanged.
    overview = directory_category_overview(records, CATEGORY_LANDING)
    overview_marker = '<section aria-label="안전한 링크 이용"'
    if directory_html.count(overview_marker) != 1:
        raise RuntimeError("Directory explanation layout changed; review required")
    help_section = directory_search_help(records, CATEGORY_LANDING)
    directory_html = directory_html.replace(
        overview_marker,
        help_section + directory_address_inspector() + overview
        + directory_purpose_comparison(records, CATEGORY_LANDING)
        + directory_everyday_task_paths(records)
        + directory_relevant_guides(posts) + overview_marker, 1)
    # Provide a structured category map for the core search landing page.
    # One declaration only; never generate unverified ratings or fake offers.
    if 'id="directory-category-schema"' in directory_html:
        raise RuntimeError("Directory category structured data already inserted")
    schema = directory_collection_schema(records, CATEGORY_LANDING)
    schema = schema.replace('<script ', '<script id="directory-category-schema" ', 1)
    if directory_html.count("</head>") != 1:
        raise RuntimeError("Directory head structure changed; schema review required")
    directory_html = directory_html.replace("</head>", schema + "</head>", 1)
    # Snapshot the complete catalog before directory.js applies URL filters.
    directory_script = re.compile(r'<script\b[^>]*src="/?assets/directory\.js(?:\?[^"]*)?"[^>]*>')
    directory_html, comparison_insertions = directory_script.subn(
        lambda match: '<script defer src="/assets/site-comparison.js"></script>' + match.group(),
        directory_html,
    )
    if comparison_insertions != 1:
        raise RuntimeError("Expected one directory search script before adding comparison")
    directory_html = directory_html.replace(
        '</body>', '<script defer src="/assets/address-inspector.js"></script></body>', 1)
    directory_html = fingerprint_directory_scripts(directory_html, OUT / "assets")
    directory_path.write_text(directory_html, encoding="utf-8")
    category_cards = []
    for category, slug, heading, purpose in CATEGORY_LANDING:
        count = counts.get(category, 0)
        if not count or not (OUT / "categories" / f"{slug}.html").is_file():
            raise RuntimeError(f"Category page or directory data missing: {category}")
        category_cards.append(
            f'<article class="v6-card"><h2><a href="/categories/{slug}">{escape(heading)}</a></h2>'
            f'<p>{escape(purpose)}</p><p>{count}개 등록 사이트</p>'
            '<p>등록 예시: ' + escape(', '.join(
                [item["name"] for item in records if item["category"] == category][:3]
            )) + '</p>'
            f'<a href="/categories/{slug}">사이트 목록 보기</a></article>')
    hub = ('<div class="wrap blog-wrap"><nav class="blog-breadcrumb"><a href="/">홈</a> / 분야별 사이트</nav>'
           '<div class="blog-heading"><p class="eyebrow">LINKWIKI · DIRECTORY</p>'
           '<h1>분야별 사이트모음·링크모음</h1>'
           '<p>필요한 분야를 선택하면 등록된 사이트의 이름과 주소, 이용 목적을 살펴볼 수 있습니다.</p></div>'
           '<div class="v6-grid">' + ''.join(category_cards) + '</div>'
           '<section class="seo-guidance"><h2>사이트를 선택할 때</h2>'
           '<p>사이트 수가 많다고 더 신뢰할 수 있는 것은 아닙니다. 각 서비스의 운영 주체, 정확한 도메인, 로그인·결제 조건을 확인하세요.</p>'
           '<p>이 목록은 접속 가능 여부나 최신 주소를 실시간으로 검증한 순위표가 아닙니다.</p>'
           '<p><a href="/directory">전체 등록 사이트 검색</a> · <a href="/guides/address-check">주소 확인 방법</a></p>'
           '</section></div>')
    hub_path = OUT / "categories" / "index.html"
    hub_path.write_text(document("분야별 사이트모음·링크모음", "커뮤니티, 웹툰, 스포츠, AI 도구, 검색·포털, 영상·OTT, 해외 교민 등 분야별 사이트 목록과 주소 확인 방법을 살펴보세요.",
                                 SITE + "/categories/", hub, header, footer), encoding="utf-8")
    from seo.directory_maintenance import render as maintenance_render
    maintenance_body = maintenance_render(records, significant_updates, CATEGORY_LANDING)
    maintenance_path = OUT / "guides" / "directory-maintenance.html"
    maintenance_path.write_text(
        document("사이트모음 관리 기록과 주소 점검 범위",
                 "링크위키 등록 사이트 수와 분야별 페이지 변경 기록, 외부 주소 확인 범위를 안내합니다.",
                 SITE + "/guides/directory-maintenance",
                 maintenance_body, header, footer), encoding="utf-8")
    for category, slug, _, _ in CATEGORY_LANDING:
        path = OUT / "categories" / f"{slug}.html"
        source = path.read_text(encoding="utf-8")
        source = sync_category_card_copy(source, records, category)
        marker = '</main>'
        if source.count(marker) != 1:
            raise RuntimeError(f"Category page layout changed: {slug}")
        matched_posts = category_article_links(posts, slug)
        related_articles = (
            '<section class="wrap seo-related-links" aria-label="이 분야의 이용 가이드">'
            '<h2>이 분야의 이용 가이드</h2>'
            '<ul>' + ''.join(
                f'<li><a href="{escape(post["url"], quote=True)}">{escape(post["title"])}</a></li>'
                for post in matched_posts) + '</ul></section>'
        ) if matched_posts else ''
        source = source.replace(marker,
            category_decision_guide(slug, records) +
            related_articles + related_category_navigation(slug) +
            '<nav class="wrap seo-related-links" aria-label="다른 분야 탐색">'
            '<a href="/categories/">다른 분야 사이트모음 보기</a> · '
            '<a href="/directory">전체 사이트 검색</a></nav>' + marker, 1)
        path.write_text(source, encoding="utf-8")

    # Normalize every generated page, including the new blog pages. Do not
    # rename physical files: Cloudflare Pages maps /about to /about.html.
    for page in OUT.rglob("*.html"):
        original = page.read_text(encoding="utf-8")
        normalized = normalize_page_links(original)
        relative = page.relative_to(OUT).as_posix()
        public_path = ("/" + relative.removesuffix("index.html")
                       if page.name == "index.html" else "/" + relative.removesuffix(".html"))
        normalized = add_breadcrumb_data(normalized, public_path)
        if normalized != original:
            page.write_text(normalized, encoding="utf-8")

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    tree = ET.parse(OUT / "sitemap.xml")
    urlset = tree.getroot()
    for element in urlset.findall(f"{{{ns}}}url/{{{ns}}}loc"):
        if element.text:
            element.text = public_url(element.text)
    existing = {el.text for el in urlset.findall(f"{{{ns}}}url/{{{ns}}}loc")}
    # Hub content changes when its source changes, not on every CI deployment.
    # Without a versioned source modification date, omit lastmod instead of
    # inventing the build date. The blog index can use the latest dated post.
    dated_posts = [entry["modified"] for entry in posts if entry["modified"]]
    hub_entries = [{"url": "/categories/", "modified": None},
                   {"url": "/blog/", "modified": max(dated_posts) if dated_posts else None},
                   {"url": "/guides/directory-maintenance",
                    "modified": significant_updates.get("/directory")}]
    for entry in hub_entries + posts:
        loc = SITE + entry["url"]
        if loc in existing:
            continue
        element = ET.SubElement(urlset, f"{{{ns}}}url")
        ET.SubElement(element, f"{{{ns}}}loc").text = loc
        initial_date = entry.get("published", entry["modified"])
        if initial_date:
            ET.SubElement(element, f"{{{ns}}}lastmod").text = initial_date
        existing.add(loc)
    # Document only dated, substantive content edits (not every CI build).
    apply_significant_lastmods(urlset, significant_updates, ns)
    tree.write(OUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (OUT / "sitemap-v2.xml").write_bytes((OUT / "sitemap.xml").read_bytes())
    from seo.directory_release_gate import validate as validate_directory_release, CATEGORIES as RELEASE_CATEGORIES
    release_problems = validate_directory_release(
        (OUT / "directory.html").read_text(encoding="utf-8"),
        (OUT / "index.html").read_text(encoding="utf-8"),
        records,
        {slug: (OUT / "categories" / f"{slug}.html").read_text(encoding="utf-8")
         if (OUT / "categories" / f"{slug}.html").is_file() else ""
         for slug in RELEASE_CATEGORIES},
        (OUT / "sitemap.xml").read_text(encoding="utf-8"),
    )
    if release_problems:
        raise RuntimeError("Directory crawlability release gate failed: " +
                           "; ".join(release_problems))
    from seo.site_audit import audit_site
    problems = audit_site(OUT)
    if problems:
        raise RuntimeError("Build integrity check failed: " + "; ".join(problems))
    print(f"Built {len(posts)} blog post(s); output={OUT}")


if __name__ == "__main__":
    build()
