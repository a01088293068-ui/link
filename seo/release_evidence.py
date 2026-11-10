#!/usr/bin/env python3
"""Record deterministic facts about the built public LinkWiki release.

This is release/build evidence, not a claim of Google indexing or ranking.
Only local generated files are read. No network, secrets or API tokens.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re

CATEGORY_PATHS = {
    "검색·포털": "search",
    "영상·OTT": "video",
    "커뮤니티": "community",
    "한인교민": "korean",
    "만화": "comics-directory",
    "만화·웹툰": "webtoon",
    "스포츠": "sports",
    "AI 도구": "ai",
}


def release_evidence(dist):
    directory = dist / "assets" / "verified-directory.json"
    source = directory.read_bytes()
    records = json.loads(source)
    if not isinstance(records, list) or not records:
        raise ValueError("Published directory JSON is missing or empty")
    card_html = (dist / "directory.html").read_text(encoding="utf-8")
    cards = len(re.findall(r'<article\b[^>]*class="v6-card"', card_html))
    if cards != len(records):
        raise ValueError(f"Directory HTML has {cards} cards for {len(records)} records")
    js = (dist / "assets" / "directory.js").read_text(encoding="utf-8")
    match = re.search(r"const sites=(\[.*?\]);\s*\(\(\)=>", js, re.S)
    if match is None or json.loads(match.group(1)) != records:
        raise ValueError("Directory search JavaScript and published JSON differ")
    by_category = Counter(entry["category"] for entry in records)
    pages = {}
    for category, slug in CATEGORY_PATHS.items():
        html = (dist / "categories" / (slug + ".html")).read_text(encoding="utf-8")
        count = len(re.findall(r'<article\b[^>]*class="item"', html))
        if count != by_category[category]:
            raise ValueError(
                f"{slug}: {count} HTML entries != {by_category[category]} source records")
        pages[slug] = count
    # Both published sitemap aliases must match byte for byte. A successful
    # build must never advertise contradictory pages to Googlebot.
    sitemap = (dist / "sitemap.xml").read_bytes()
    sitemap_v2 = (dist / "sitemap-v2.xml").read_bytes()
    if sitemap != sitemap_v2:
        raise ValueError("sitemap.xml and sitemap-v2.xml differ")
    from xml.etree import ElementTree as ET
    try:
        sitemap_root = ET.fromstring(sitemap)
    except ET.ParseError as error:
        raise ValueError(f"sitemap.xml is invalid XML: {error}") from error
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {
        node.text for node in sitemap_root.findall("sm:url/sm:loc", ns) if node.text
    }
    required_urls = {
        "https://linkwiki.info/",
        "https://linkwiki.info/directory",
        "https://linkwiki.info/categories/",
    }
    required_urls.update(
        "https://linkwiki.info/categories/" + slug
        for slug in CATEGORY_PATHS.values()
    )
    if not required_urls.issubset(sitemap_urls):
        raise ValueError("sitemap.xml missing core canonical URLs: "
                         + ", ".join(sorted(required_urls - sitemap_urls)))
    robots = (dist / "robots.txt").read_text(encoding="utf-8")
    for name in ("sitemap.xml", "sitemap-v2.xml"):
        if "Sitemap: https://linkwiki.info/" + name not in robots:
            raise ValueError(f"robots.txt does not advertise {name}")
    home = (dist / "index.html").read_text(encoding="utf-8")
    if f"{len(records)}개 사이트" not in home:
        raise ValueError("Homepage does not display the current total")
    return {
        "status": "build_verified",
        "scope": "local_generated_release_only",
        "sites": len(records),
        "categories": pages,
        "directory_cards": cards,
        "js_records": len(records),
        "directory_json_sha256": sha256(source).hexdigest(),
        "directory_html_sha256": sha256(card_html.encode("utf-8")).hexdigest(),
        "directory_js_sha256": sha256(js.encode("utf-8")).hexdigest(),
        "sitemap_sha256": sha256(sitemap).hexdigest(),
        "sitemap_url_count": len(sitemap_urls),
        "google_indexing_verified": False,
        "public_deployment_verified": False,
        "rank_improvement_verified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--commit", default="", help="Exact checked-out source SHA")
    parser.add_argument("--output", type=Path, default=Path("seo/release-build-evidence.json"))
    args = parser.parse_args()
    result = release_evidence(args.dist)
    if args.commit:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", args.commit):
            parser.error("--commit must be a full 40-digit Git commit SHA")
        result["source_commit"] = args.commit.lower()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"PASS: {result['sites']} static directory entries; "
          f"{len(result['categories'])} categories; "
          f"release evidence saved: {args.output}")


if __name__ == "__main__":
    main()
