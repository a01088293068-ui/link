#!/usr/bin/env python3
"""Analyze crawlable internal HTML links without guessing at Google rankings."""
from pathlib import Path
from datetime import datetime, timezone
import json
import sys
from site_audit import SITE, internal_inbound_links

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUTPUT = ROOT / "seo" / "internal-link-report.md"
TARGETS = (
    "/", "/directory", "/categories/",
    "/categories/community", "/categories/korean", "/categories/comics-directory",
    "/categories/webtoon", "/categories/ai", "/categories/search",
    "/categories/sports", "/categories/video",
    "/guides/address-check", "/guides/directory-comparison",
    "/guides/link-troubleshooting",
)

def report(directory, targets=TARGETS):
    directory = Path(directory)
    inbound = internal_inbound_links(directory)
    report_lines = [
        "# LinkWiki static internal HTML link audit",
        "",
        "Generated: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "",
        "Counts are distinct source HTML pages with actual anchor tags. "
        "Sitemap entries, JS navigation or Google index status are not counted.",
        "",
        "| Public path | Unique inbound pages | Home links to page | Directory links to page |",
        "|---|---:|---|---|",
    ]
    for path in targets:
        sources = inbound.get(path, set())
        report_lines.append(
            f"| {SITE}{path} | {len(sources)} | "
            f"{'yes' if '/' in sources else 'no'} | "
            f"{'yes' if '/directory' in sources else 'no'} |")
    orphans = [path for path in targets if path != "/" and not inbound.get(path)]
    report_lines += ["", "## Core link-graph risks", ""]
    if orphans:
        report_lines += ["Orphaned core target(s) in generated HTML:", ""]
        report_lines += ["- " + SITE + path for path in orphans]
    else:
        report_lines += ["No orphaned core targets in generated HTML."]
    report_lines += ["", "A low link count is an internal navigation signal only, not proof of an SEO penalty.", ""]
    return "\n".join(report_lines)

def main():
    if not DIST.is_dir():
        sys.stderr.write("Build dist first: python3 build.py\n")
        return 2
    OUTPUT.write_text(report(DIST), encoding="utf-8")
    print(OUTPUT)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
