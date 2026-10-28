#!/usr/bin/env python3
"""Verify the generated Pages release before Cloudflare publishes it.

This checks local build consistency, not Google's indexing status.
"""
from pathlib import Path
import json
import re
import sys
from urllib.parse import unquote, urlsplit
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


def audit_site(dist):
    dist = Path(dist)
    errors = []
    sitemap = dist / "sitemap.xml"
    try:
        root = ET.parse(sitemap).getroot()
        locs = {entry.text for entry in root.iter() if entry.tag.endswith("}loc") and entry.text}
    except (ET.ParseError, OSError) as error:
        return [f"sitemap cannot be read: {error}"]

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
    for page in dist.rglob("*.html"):
        if page.name == "404.html":
            continue
        relative = page.relative_to(dist).as_posix()
        public_path = ("/" + relative.removesuffix("index.html")
                       if page.name == "index.html" else "/" + relative.removesuffix(".html"))
        content = page.read_text(encoding="utf-8")
        if "공개 전 미리보기" in content:
            errors.append(f"stale preview notice on public page: {relative}")
        # Search engine ownership proof files are plain text despite .html.
        if not re.search(r"<html\b", content, re.I):
            continue
        canonical = re.search(r'<link\b[^>]*\brel="canonical"[^>]*\bhref="([^"]+)"', content)
        if not canonical:
            canonical = re.search(r'<link\b[^>]*\bhref="([^"]+)"[^>]*\brel="canonical"', content)
        if not canonical or canonical.group(1) != SITE + public_path:
            errors.append(f"noncanonical page URL: {relative}")
        for href in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', content):
            if href.startswith(SITE + "/") or href.startswith("/") and not href.startswith("//"):
                if urlsplit(href).path.endswith(".html"):
                    errors.append(f"redirecting internal link: {relative} -> {href}")

    # Verify stored addresses are well formed. This DOES NOT mean destinations
    # were visited or that the linked services have been independently vetted.
    directory = dist / "assets" / "verified-directory.json"
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

    posts = sorted((dist / "blog").glob("*/index.html"))
    for post in posts:
        relative = post.relative_to(dist).as_posix().removesuffix("index.html")
        canonical = SITE + "/" + relative
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
