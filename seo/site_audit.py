#!/usr/bin/env python3
"""Verify the generated Pages release before Cloudflare publishes it.

This checks local build consistency, not Google's indexing status.
"""
from pathlib import Path
from html import unescape
import json
import re
import sys
from urllib.parse import unquote, urlsplit, urljoin
import xml.etree.ElementTree as ET

SITE = "https://linkwiki.info"


def page_file(dist, path):
    """Resolve only same-site paths; never read outside the dist directory."""
    clean = unquote(urlsplit(path).path)
    if not clean.startswith("/") or "\\" in clean:
        return None
    parts = Path(clean.lstrip("/")).parts
    if ".." in parts:
        return None
    destination = dist.joinpath(*parts)
    if clean.endswith("/"):
        return destination / "index.html"
    if destination.suffix == "":
        return destination.with_suffix(".html")
    return destination



def has_noindex_meta(content):
    """Detect robots noindex regardless of HTML meta attribute order."""
    for tag in re.findall(r'<meta\b[^>]*>', content, flags=re.I | re.S):
        attrs = {name.lower(): value for name, value in re.findall(
            r"""([a-zA-Z_:][-a-zA-Z0-9_:]*)\s*=\s*["']([^"']*)["']""", tag)}
        if attrs.get("name", "").lower() not in ("robots", "googlebot"):
            continue
        directives = re.split(r'[\s,]+', attrs.get("content", "").lower())
        if "noindex" in directives or "none" in directives:
            return True
    return False


def internal_inbound_links(dist):
    """Map public URLs to distinct HTML pages linking to them."""
    inbound = {}
    for source in Path(dist).rglob("*.html"):
        text = source.read_text(encoding="utf-8")
        if not re.search(r"<html\b", text, re.I):
            continue
        relative = source.relative_to(dist).as_posix()
        source_path = ("/" + relative.removesuffix("index.html")
                       if source.name == "index.html"
                       else "/" + relative.removesuffix(".html"))
        for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', text, re.I):
            target = urlsplit(urljoin(SITE + source_path, href))
            if target.scheme != "https" or target.netloc != "linkwiki.info":
                continue
            path = target.path
            if path.endswith(".html"):
                path = path[:-5]
            if path == "/index":
                path = "/"
            if path == source_path:
                continue
            inbound.setdefault(path, set()).add(source_path)
    return inbound


def card_copy(block, title_tag):
    """Read visible site metadata from an existing static directory card."""
    def contents(tag):
        match = re.search(r'<'+tag+r'\b[^>]*>(.*?)</'+tag+r'>', block, re.I | re.S)
        return unescape(re.sub(r'<[^>]+>', '', match.group(1))).strip() if match else None
    name = contents(title_tag)
    description = contents("p")
    category = contents("small")
    domain_tag = re.search(r'<span\b[^>]*\bclass="site-domain"[^>]*>(.*?)</span>',
                           block, re.I | re.S)
    domain = (unescape(re.sub(r'<[^>]+>', '', domain_tag.group(1))).strip()
              if domain_tag else None)
    return {"name": name, "description": description,
            "category": category, "domain": domain}


def card_copy_errors(blocks, records, title_tag, label):
    """Detect stale names, descriptions and domains despite matching hrefs."""
    errors = []
    for number, (block, record) in enumerate(zip(blocks, records), 1):
        if not isinstance(record, dict):
            continue
        actual = card_copy(block, title_tag)
        url = record.get("url", "")
        hostname = urlsplit(url).hostname if isinstance(url, str) else None
        for field, expected in (
            ("name", record.get("name")),
            ("description", record.get("description")),
            ("category", record.get("category")),
            ("domain", hostname),
        ):
            if actual[field] != expected:
                errors.append(f"{label} card #{number} {field} differs from JSON")
    return errors


def audit_site(dist):
    dist = Path(dist)
    errors = []
    sitemap = dist / "sitemap.xml"
    try:
        root = ET.parse(sitemap).getroot()
        loc_list = [entry.text for entry in root.iter()
                    if entry.tag.endswith("}loc") and entry.text]
        locs = set(loc_list)
        if len(locs) != len(loc_list):
            errors.append("duplicate URL in sitemap")
    except (ET.ParseError, OSError) as error:
        return [f"sitemap cannot be read: {error}"]

    robots_file = dist / "robots.txt"
    if not robots_file.is_file():
        errors.append("robots.txt missing from build")
    else:
        robots_text = robots_file.read_text(encoding="utf-8-sig")
        robots_lines = [
            line.split("#", 1)[0].strip()
            for line in robots_text.splitlines()
        ]
        robots_lines = [line for line in robots_lines if line]
        normalized = [line.lower().replace(" ", "") for line in robots_lines]
        if "sitemap:https://linkwiki.info/sitemap.xml" not in normalized:
            errors.append("robots.txt missing canonical sitemap URL")
        # A global block is a critical crawlability regression. A targeted
        # disallow for sensitive paths is allowed.
        all_agents = False
        for line in robots_lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                all_agents = value == "*"
            elif key == "disallow" and all_agents and value == "/":
                errors.append("robots.txt globally disallows crawling")
                break

    v2 = dist / "sitemap-v2.xml"
    if not v2.is_file() or v2.read_bytes() != sitemap.read_bytes():
        errors.append("sitemap-v2.xml differs from sitemap.xml")
    blog_index = dist / "blog" / "index.html"
    if not blog_index.is_file() or SITE + "/blog/" not in locs:
        errors.append("blog index missing from build or sitemap")

    for loc in locs:
        if not loc.startswith(SITE + "/"):
            errors.append(f"non-site sitemap URL: {loc}")
        elif urlsplit(loc).path.endswith(".html"):
            errors.append(f"redirecting .html URL in sitemap: {loc}")
        elif (resolved := page_file(dist, loc[len(SITE):])) is None or not resolved.is_file():
            errors.append(f"sitemap URL without generated page: {loc}")

    # Every canonical must match a non-redirecting URL in the sitemap.
    titles_seen = {}
    for page in dist.rglob("*.html"):
        if page.name == "404.html":
            continue
        relative = page.relative_to(dist).as_posix()
        public_path = ("/" + relative.removesuffix("index.html")
                       if page.name == "index.html" else "/" + relative.removesuffix(".html"))
        content = page.read_text(encoding="utf-8")
        if "공개 전 미리보기" in content:
            errors.append(f"stale preview notice on public page: {relative}")
        if has_noindex_meta(content):
            errors.append(f"indexable page blocked by robots noindex: {relative}")
        # Search engine ownership proof files are plain text despite .html.
        if not re.search(r"<html\b", content, re.I):
            continue
        canonical = re.search(r'<link\b[^>]*\brel="canonical"[^>]*\bhref="([^"]+)"', content)
        if not canonical:
            canonical = re.search(r'<link\b[^>]*\bhref="([^"]+)"[^>]*\brel="canonical"', content)
        if not canonical or canonical.group(1) != SITE + public_path:
            errors.append(f"noncanonical page URL: {relative}")
        if SITE + public_path not in locs:
            errors.append(f"indexable page missing from sitemap: {relative}")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.I | re.S)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
        if not title:
            errors.append(f"missing HTML title: {relative}")
        elif title in titles_seen:
            errors.append(f"duplicate HTML title: {relative} and {titles_seen[title]}")
        else:
            titles_seen[title] = relative
        # Every indexable HTML page needs a useful search-result description.
        # This catches accidentally empty/missing metadata on new articles.
        meta_descriptions = []
        for meta_tag in re.findall(r'<meta\b[^>]*>', content, re.I | re.S):
            attributes = {
                name.lower(): value
                for name, value in re.findall(
                    r"""([a-zA-Z_:][-a-zA-Z0-9_:]*)\s*=\s*["']([^"']*)["']""",
                    meta_tag)
            }
            if attributes.get("name", "").lower() == "description":
                meta_descriptions.append(attributes.get("content", "").strip())
        if len(meta_descriptions) != 1 or not meta_descriptions[0]:
            errors.append(f"missing, empty or duplicate meta description: {relative}")
        # Validate all structured-data scripts and the canonical breadcrumb trail.
        for script in re.findall(
                r'<script\b[^>]*\btype="application/ld\+json"[^>]*>(.*?)</script>',
                content, re.I | re.S):
            try:
                data = json.loads(script)
            except ValueError as error:
                errors.append(f"invalid JSON-LD: {relative}: {error}")
                continue
            schemas = data.get("@graph", []) if isinstance(data, dict) and "@graph" in data else [data]
            if not isinstance(schemas, list):
                errors.append(f"invalid JSON-LD graph: {relative}")
                continue
            for schema in schemas:
                if not isinstance(schema, dict) or schema.get("@type") != "BreadcrumbList":
                    continue
                items = schema.get("itemListElement")
                if not isinstance(items, list) or len(items) < 2:
                    errors.append(f"invalid breadcrumb list: {relative}")
                    continue
                positions = [item.get("position") if isinstance(item, dict) else None for item in items]
                if positions != list(range(1, len(items) + 1)):
                    errors.append(f"invalid breadcrumb positions: {relative}")
                if not isinstance(items[-1], dict) or items[-1].get("item") != SITE + public_path:
                    errors.append(f"breadcrumb URL mismatch: {relative}")
                if not isinstance(items[0], dict) or items[0].get("item") != SITE + "/":
                    errors.append(f"breadcrumb home mismatch: {relative}")
        for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', content):
            if href.startswith(SITE + "/") or href.startswith("/") and not href.startswith("//"):
                local_href = href[len(SITE):] if href.startswith(SITE + "/") else href
                if urlsplit(local_href).path.endswith(".html"):
                    errors.append(f"redirecting internal link: {relative} -> {href}")
                target = page_file(dist, local_href)
                if target is None or not target.is_file():
                    errors.append(f"broken internal navigation link: {relative} -> {href}")

    # Verify stored addresses are well formed. This DOES NOT mean destinations
    # were visited or that the linked services have been independently vetted.
    directory = dist / "assets" / "verified-directory.json"
    records = None
    try:
        records = json.loads(directory.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            errors.append("directory records missing or empty")
        else:
            seen = set()
            for number, record in enumerate(records, 1):
                if not isinstance(record, dict):
                    errors.append(f"invalid directory record #{number}")
                    continue
                url = record.get("url", "")
                parts = urlsplit(url) if isinstance(url, str) else urlsplit("")
                if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                    errors.append(f"invalid directory URL #{number}")
                if url in seen:
                    errors.append(f"duplicate directory URL #{number}")
                seen.add(url)
                if not all(isinstance(record.get(k), str) and record[k].strip()
                           for k in ("name", "category", "description")):
                    errors.append(f"directory metadata incomplete #{number}")
    except (OSError, ValueError) as error:
        errors.append(f"directory data cannot be read: {error}")

    # Search-intent landing page counts must reflect the same directory source
    # used for the indexable static listing. Detect stale editorial numbers.
    homepage = dist / "index.html"
    if homepage.is_file() and isinstance(records, list) and records:
        home_html = homepage.read_text(encoding="utf-8")
        for label in ("등록 사이트", "등록 항목"):
            values = [int(value) for value in re.findall(
                rf"(\d+)개\s+{re.escape(label)}", home_html)]
            if not values:
                errors.append(f"homepage missing directory count: {label}")
            elif any(value != len(records) for value in values):
                errors.append(f"homepage directory count mismatch: {label}")

    # The visible directory cards are statically crawlable. Keep them in sync
    # with the editable JSON source so Google and on-page search see the same list.
    directory_page = dist / "directory.html"
    if directory_page.is_file() and isinstance(records, list):
        listing = directory_page.read_text(encoding="utf-8")
        card_blocks = re.findall(
            r'<article\s+class="v6-card"[^>]*>(.*?)</article>', listing, re.I | re.S)
        card_urls = []
        for block in card_blocks:
            anchors = re.findall(r'<a\b[^>]*\bhref="(https://[^"]+)"', block)
            if len(anchors) != 1:
                errors.append("directory card has missing/multiple destination links")
            else:
                card_urls.append(anchors[0])
        expected_urls = [item.get("url") for item in records if isinstance(item, dict)]
        if len(card_blocks) != len(expected_urls):
            errors.append(f"directory card count differs from JSON: {len(card_blocks)} != {len(expected_urls)}")
        if card_urls != expected_urls:
            errors.append("directory card URL order/content differs from JSON source")
        if listing.count('class="lw-safety-note seo-search-help"') != 1:
            errors.append("directory usage guide missing or duplicated")
        if "사이트모음 검색 및 확인 방법" not in listing:
            errors.append("directory search help missing accessible label")
        for expected_path in ("/categories/", "/guides/address-check",
                              "/guides/link-troubleshooting"):
            if f'href="{expected_path}"' not in listing:
                errors.append(f"directory guide missing help link: {expected_path}")
        for slug in ("community", "korean", "comics-directory", "webtoon",
                     "ai", "search", "sports", "video"):
            if f'href="/categories/{slug}"' not in listing:
                errors.append(f"directory missing category navigation: {slug}")
        errors.extend(card_copy_errors(card_blocks, records, "h3", "directory"))

    category_pages = {
        "ai": "AI 도구", "search": "검색·포털", "sports": "스포츠",
        "community": "커뮤니티", "korean": "한인교민",
        "video": "영상·OTT", "webtoon": "만화·웹툰",
        "comics-directory": "만화",
    }
    if isinstance(records, list):
        for slug, category in category_pages.items():
            category_page = dist / "categories" / f"{slug}.html"
            if not category_page.is_file():
                continue
            page_content = category_page.read_text(encoding="utf-8")
            # Category cards use two existing templates: .item and .v6-card.
            blocks = re.findall(
                r'<article\b[^>]*\bclass="(?:item|v6-card)"[^>]*>(.*?)</article>',
                page_content, re.I | re.S)
            actual_urls = []
            for block in blocks:
                links = re.findall(r'<a\b[^>]*\bhref="(https://[^"]+)"', block)
                if len(links) != 1:
                    errors.append(f"invalid category card destination: {slug}")
                else:
                    actual_urls.append(links[0])
            expected_urls = [record.get("url") for record in records
                             if isinstance(record, dict) and record.get("category") == category]
            if actual_urls != expected_urls:
                errors.append(f"category card URLs differ from JSON: {slug}")
            expected_records = [record for record in records
                                if isinstance(record, dict) and record.get("category") == category]
            # Legacy category pages render .v6-card with h3; newer .item cards
            # use strong. Both are supported and must match the same JSON data.
            title_tag = "strong" if blocks and re.search(r'<strong\b', blocks[0], re.I) else "h3"
            errors.extend(card_copy_errors(blocks, expected_records, title_tag, slug))

    # Sitemap inclusion alone does not make a page discoverable through links.
    # Require HTML entry points for the main list and every published article.
    inbound = internal_inbound_links(dist)
    if directory_page.is_file() and not inbound.get("/directory"):
        errors.append("orphan core directory page: /directory")
    posts = sorted((dist / "blog").glob("*/index.html"))
    for post in posts:
        relative = post.relative_to(dist).as_posix().removesuffix("index.html")
        canonical = SITE + "/" + relative
        if not inbound.get("/" + relative):
            errors.append(f"orphan published article: {relative}")
        if canonical not in locs:
            errors.append(f"post absent from sitemap: {relative}")
        html = post.read_text(encoding="utf-8")
        if f'href="{canonical}"' not in html:
            errors.append(f"canonical missing or incorrect: {relative}")
        # Inspect internal article links; ignore external destinations and fragments.
        article = html.split('<div class="blog-content">', 1)
        if len(article) < 2:
            errors.append(f"article body missing: {relative}")
            continue
        article_body = article[1].split('</div>', 1)[0]
        for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', article_body):
            if not href.startswith("/") or href.startswith("//"):
                continue
            target = page_file(dist, href)
            if target is None or not target.is_file():
                errors.append(f"broken internal article link: {relative} -> {href}")
    return errors


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "dist"
    problems = audit_site(output)
    for problem in problems:
        print("FAIL:", problem)
    if problems:
        sys.exit(1)
    print("PASS: sitemap, canonical URLs and internal post links verified")
