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
        "google_indexing_verified": False,
        "public_deployment_verified": False,
        "rank_improvement_verified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, default=Path("seo/release-build-evidence.json"))
    args = parser.parse_args()
    result = release_evidence(args.dist)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"PASS: {result['sites']} static directory entries; "
          f"{len(result['categories'])} categories; "
          f"release evidence saved: {args.output}")


if __name__ == "__main__":
    main()
