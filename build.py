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
        article = (f'<div class="wrap blog-wrap"><nav class="blog-breadcrumb"><a href="/">홈</a> / '
                   f'<a href="/blog/">사이트 정보</a></nav><article class="blog-article">'
                   f'<p class="eyebrow">LINKWIKI · 사이트 정보</p><h1>{escape(title)}</h1>'
                   + (f'<p class="blog-date">{display_date}</p>' if display_date else '') +
                   f'<div class="blog-content">{markdown(body)}</div>'
                   '<div class="blog-bottom"><a href="/blog/">다른 이용 가이드 보기</a>'
                   '<a href="/directory.html">사이트 목록 살펴보기</a></div></article></div>')
        target = OUT / "blog" / name / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document(title, desc, canonical, article, header, footer), encoding="utf-8")
        posts.append({"title": title, "description": desc, "url": url, "date": display_date,
                      "modified": datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).date().isoformat()})

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
    home = (OUT / "index.html").read_text(encoding="utf-8")
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

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    tree = ET.parse(OUT / "sitemap.xml")
    urlset = tree.getroot()
    existing = {el.text for el in urlset.findall(f"{{{ns}}}url/{{{ns}}}loc")}
    for entry in [{"url": "/blog/", "modified": datetime.now(timezone.utc).date().isoformat()}] + posts:
        loc = SITE + entry["url"]
        if loc in existing:
            continue
        element = ET.SubElement(urlset, f"{{{ns}}}url")
        ET.SubElement(element, f"{{{ns}}}loc").text = loc
        ET.SubElement(element, f"{{{ns}}}lastmod").text = entry["modified"]
        existing.add(loc)
    tree.write(OUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (OUT / "sitemap-v2.xml").write_bytes((OUT / "sitemap.xml").read_bytes())
    print(f"Built {len(posts)} blog post(s); output={OUT}")


if __name__ == "__main__":
    build()
