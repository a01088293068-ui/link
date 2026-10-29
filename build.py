#!/usr/bin/env python3
"""Build LinkWiki's existing static pages plus a Markdown-driven guide journal.

Cloudflare Pages: build command `python3 build.py`; output directory `dist`.
No third-party dependencies, no external network calls, no overwrites of source.
"""
from datetime import datetime, timezone
from html import escape
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
    ("만화·웹소설", "comics-directory", "만화·웹소설 사이트모음", "장르별 만화·웹소설 플랫폼의 작품 유형과 유료 이용 조건을 비교하세요."),
    ("만화·웹툰", "webtoon", "웹툰 링크모음", "웹툰 서비스별 작품 유형과 공식 이용 경로를 비교하세요."),
    ("AI 도구", "ai", "AI 도구 사이트모음", "글쓰기·검색·요약 도구를 기능과 이용 조건에 따라 비교하세요."),
    ("검색·포털", "search", "검색·포털 링크모음", "검색과 정보 탐색에 필요한 포털 서비스를 골라보세요."),
    ("스포츠", "sports", "스포츠 사이트모음", "일정·기록·뉴스 등 목적에 따라 서비스를 찾고 중계권을 확인하세요."),
    ("영상·OTT", "video", "영상·OTT 링크모음", "영상 서비스의 콘텐츠 제공 방식과 구독 조건을 구분해 살펴보세요."),
)


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
    for raw in body.splitlines():
        line = raw.strip()
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
    edits = (
        (
            '분야별 사이트를 비교하고, 주소 확인부터 접속 문제 해결까지 링크위키에서 살펴보세요.',
            '링크위키 주소모음·링크모음에서 분야별 사이트를 찾고, 실제 이동 주소와 이용 조건을 확인해 보세요.',
        ),
        ('<label for="lw-home-query">사이트 이름으로 찾기</label>',
         '<label for="lw-home-query">사이트 이름·주소 검색</label>'),
        (
            '이 사이트의 97개 등록 항목을 이름·분야·도메인으로 검색합니다.</p>',
            '이 사이트의 97개 등록 항목을 이름·분야·도메인으로 검색합니다.</p>'
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
            # The homepage now uses a more specific, fact-checked 97-site summary.
            if "97개 등록 사이트를 분야별로 검색하고 비교하세요." not in home:
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


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    # Preserve all existing features and assets; only add a discreet nav item to HTML pages.
    for child in ROOT.iterdir():
        if child.name in {"dist", "content", "seo", ".github", ".git", "build.py", "README-AUTO-BLOG.md", "SEO-AUTOMATION-SETUP.md", "QA-REPORT.txt", "__pycache__", "tests"}:
            continue
        if child.is_dir():
            shutil.copytree(child, OUT / child.name)
        elif child.is_file():
            shutil.copy2(child, OUT / child.name)
    for existing_page in OUT.rglob('*.html'):
        existing_html = existing_page.read_text(encoding='utf-8')
        improved_html = add_nav(existing_html)
        if improved_html != existing_html:
            existing_page.write_text(improved_html, encoding='utf-8')
    header, footer = chrome()
    posts = []
    for source in sorted(POSTS.glob("*.md"), reverse=True) if POSTS.exists() else []:
        body = source.read_text(encoding="utf-8-sig")
        if not body.strip() or len(body.strip()) < 150:
            continue
        name = slug_for(source)
        title = extract_title(body)
        desc = excerpt(re.sub(r'^#.*$', '', body, count=1, flags=re.M))
        date = re.search(r'20\d{6}', source.stem)
        date_text = date.group() if date else ""
        if date_text:
            try:
                display_date = datetime.strptime(date_text, "%Y%m%d").strftime("%Y.%m.%d")
            except ValueError:
                display_date = ""
        else:
            display_date = ""
        url = f"/blog/{quote(name)}/"
        canonical = SITE + url
        content_body = re.sub(r'^#\s+.*(?:\n|$)', '', body, count=1)
        article = (f'<div class="wrap blog-wrap"><nav class="blog-breadcrumb"><a href="/">홈</a> / '
                   f'<a href="/blog/">사이트 정보</a></nav><article class="blog-article">'
                   f'<p class="eyebrow">LINKWIKI · 사이트 정보</p><h1>{escape(title)}</h1>'
                   + (f'<p class="blog-date">{display_date}</p>' if display_date else '') +
                   f'<div class="blog-content">{markdown(content_body)}</div>'
                   '<div class="blog-bottom"><a href="/">주소모음·링크모음 홈</a>'
                   '<a href="/blog/">다른 이용 가이드 보기</a>'
                   '<a href="/directory.html">사이트 목록 살펴보기</a></div></article></div>')
        target = OUT / "blog" / name / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document(title, desc, canonical, article, header, footer), encoding="utf-8")
        posts.append({"title": title, "description": desc, "url": url, "date": display_date,
                      "modified": stable_post_lastmod(source)})

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
    home = home.replace(position, panel + position, 1)
    home = home.replace('</head>', '<link href="/assets/blog.css" rel="stylesheet"/></head>', 1)
    (OUT / "index.html").write_text(home, encoding="utf-8")

    # One useful navigation hub backed by existing registered sites, not eight
    # duplicate keyword doorway pages. Individual category pages remain intact.
    records = json.loads((OUT / "assets" / "verified-directory.json").read_text(encoding="utf-8"))
    counts = {}
    for record in records:
        counts[record["category"]] = counts.get(record["category"], 0) + 1
    category_cards = []
    for category, slug, heading, purpose in CATEGORY_LANDING:
        count = counts.get(category, 0)
        if not count or not (OUT / "categories" / f"{slug}.html").is_file():
            raise RuntimeError(f"Category page or directory data missing: {category}")
        category_cards.append(
            f'<article class="v6-card"><h2><a href="/categories/{slug}">{escape(heading)}</a></h2>'
            f'<p>{escape(purpose)}</p><p>{count}개 등록 사이트</p>'
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
    for category, slug, _, _ in CATEGORY_LANDING:
        path = OUT / "categories" / f"{slug}.html"
        source = path.read_text(encoding="utf-8")
        marker = '</main>'
        if source.count(marker) != 1:
            raise RuntimeError(f"Category page layout changed: {slug}")
        source = source.replace(marker,
            '<nav class="wrap seo-related-links" aria-label="다른 분야 탐색">'
            '<a href="/categories/">다른 분야 사이트모음 보기</a> · '
            '<a href="/directory">전체 사이트 검색</a></nav>' + marker, 1)
        path.write_text(source, encoding="utf-8")

    # Normalize every generated page, including the new blog pages. Do not
    # rename physical files: Cloudflare Pages maps /about to /about.html.
    for page in OUT.rglob("*.html"):
        original = page.read_text(encoding="utf-8")
        normalized = normalize_page_links(original)
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
                   {"url": "/blog/", "modified": max(dated_posts) if dated_posts else None}]
    for entry in hub_entries + posts:
        loc = SITE + entry["url"]
        if loc in existing:
            continue
        element = ET.SubElement(urlset, f"{{{ns}}}url")
        ET.SubElement(element, f"{{{ns}}}loc").text = loc
        if entry["modified"]:
            ET.SubElement(element, f"{{{ns}}}lastmod").text = entry["modified"]
        existing.add(loc)
    tree.write(OUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (OUT / "sitemap-v2.xml").write_bytes((OUT / "sitemap.xml").read_bytes())
    from seo.site_audit import audit_site
    problems = audit_site(OUT)
    if problems:
        raise RuntimeError("Build integrity check failed: " + "; ".join(problems))
    print(f"Built {len(posts)} blog post(s); output={OUT}")


if __name__ == "__main__":
    build()
