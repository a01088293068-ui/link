#!/usr/bin/env python3
"""Discover relevant editorial outreach prospects. Never posts or registers links."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "seo/backlink-registry.json"
OUTPUT = ROOT / "seo/backlink-prospects.json"
REPORT = ROOT / "seo/backlink-prospects.md"
SEARCH_API = "https://google.serper.dev/search"
QUERIES = (
    '"submit website" "editorial" "web directory"',
    '"submit site" "reviewed" "directory"',
    '"suggest a resource" "website directory"',
    '"add website" "Korean" "directory"',
    '"submit resource" "internet safety" "directory"',
    '"add url" "curated web directory"',
)

BLOCKED_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "instagram.com", "x.com",
    "pinterest.com", "linkedin.com", "reddit.com", "github.com", "linkwiki.info",
}
NEGATIVE = (
    "buy backlinks", "guest post packages", "pbn", "link exchange",
    "reciprocal link required", "casino backlinks", "1000 links",
    "bulk submission", "paid links", "submit to 100", "adult websites",
    "phonesex", "porn", "gambling", "betting", "casino", "seo agency",
    "link building services", "link-building services", "backlink packages",
    "submit website feedback", "submit inquiry", "staff directory",
    "department directory", "employee directory",
)
RELEVANT = ("directory", "resource", "website", "site", "submit", "editorial",
            "suggest", "korean", "curated", "listing", "link")
INTENT = ("submit", "suggest", "add site", "add url", "get listed", "listing", "contribute")
# Avoid mistaking footer text ("submit website feedback") for an
# editorial website listing opportunity. Require topical title evidence.
SUBMISSION_TITLE = (
    "submit website", "submit your website", "submit site", "submit a site",
    "add website", "add your website", "add site", "add a site", "add url",
    "suggest a resource", "submit resource", "submit a resource",
    "get listed", "submit link", "submit a link", "website submission",
    "directory submission", "web directory", "website directory",
    "resource directory",
)
UNRELATED_PATHS = (
    "/staff/", "/department/", "/employees/", "/terms-of-use",
    "/privacy-policy", "/sitemap", "/news/", "/article/",
)


def hostname(url):
    parsed = urlsplit(str(url))
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme != "https" or not host or host == "localhost":
        return ""
    return host


def existing_domains(registry):
    domains = set()
    for entry in registry.get("entries", []):
        for key in ("submission_url", "public_url"):
            host = hostname(entry.get(key, ""))
            if host:
                domains.add(host)
    return domains


def blocked(host, known):
    return any(host == d or host.endswith("." + d) for d in known | BLOCKED_DOMAINS)


def assess(result, known):
    url = str(result.get("link") or "")
    host = hostname(url)
    if not host or blocked(host, known):
        return None
    title = re.sub(r"\s+", " ", str(result.get("title") or "")).strip()[:180]
    snippet = re.sub(r"\s+", " ", str(result.get("snippet") or "")).strip()[:420]
    content = (title + " " + snippet).lower()
    if any(term in content for term in NEGATIVE):
        return None
    path = urlsplit(url).path.lower()
    if any(part in path for part in UNRELATED_PATHS):
        return None
    title_text = title.lower()
    if not any(term in title_text for term in SUBMISSION_TITLE):
        return None
    # A generic "directory" or "website" is not evidence of third-party
    # submission eligibility; snippets alone can be misleading.
    has_editorial_context = any(term in content for term in
                                 ("web directory", "website directory",
                                  "curated", "editorial", "resource directory"))
    if not has_editorial_context:
        return None
    relevance = sorted({word for word in RELEVANT if word in content})
    intent = sorted({word for word in INTENT if word in content})
    if len(relevance) < 2 or not intent:
        return None
    score = min(70, len(relevance) * 7 + len(intent) * 8)
    # Scores only order leads; they are NOT authority/trust measurements.
    return {
        "domain": host, "url": url, "title": title, "snippet": snippet,
        "lead_score": score, "relevance_terms": relevance, "intent_terms": intent,
        "status": "manual_policy_review", "quality_verified": False,
        "submission_sent": False,
    }


def search(query, key):
    payload = json.dumps({"q": query, "num": 10, "gl": "us", "hl": "en"}).encode()
    request = Request(SEARCH_API, payload, {
        "X-API-KEY": key, "Content-Type": "application/json",
        "Accept": "application/json", "User-Agent": "LinkWiki-OutreachResearch/1.0"
    }, method="POST")
    with urlopen(request, timeout=25) as response:
        data = json.load(response)
    return data.get("organic", [])


def discover(search_fn, registry, queries=QUERIES):
    known = existing_domains(registry)
    leads = {}
    errors = []
    for query in queries:
        try:
            results = search_fn(query)
        except (ValueError, OSError, TimeoutError) as exc:
            errors.append(f"{query}: {type(exc).__name__}: {str(exc)[:100]}")
            continue
        for result in results:
            candidate = assess(result, known)
            if not candidate:
                continue
            host = candidate["domain"]
            if host not in leads or candidate["lead_score"] > leads[host]["lead_score"]:
                candidate["found_via"] = query
                leads[host] = candidate
    return sorted(leads.values(), key=lambda x: (-x["lead_score"], x["domain"])), errors


def report_text(leads, errors, observed):
    out = [
        "# LinkWiki 백링크 제휴·등록 후보 (자동 탐색)", "",
        f"검색 시각: {observed}", f"신규 도메인 후보: {len(leads)}개", "",
        "이는 검색 결과 기반 후보이며 고품질·게재 가능성·도메인 권위를 검증하지 않았습니다.",
        "사이트 정책, 독자 적합성, 편집 심사와 개인정보 요구를 사람이 확인한 후에만 접촉합니다.",
        "이 자동화는 외부 사이트에 글·링크·이메일을 전송하지 않습니다.", "",
        "| 후보 | 점수* | 검색 근거 | 검토 상태 |", "|---|---:|---|---|",
    ]
    for lead in leads:
        title = lead["title"].replace("|", " ").replace("]", "")
        url = lead["url"].replace(")", "%29")
        out.append(f'| [{title}]({url}) | {lead["lead_score"]} | {", ".join(lead["relevance_terms"])} | 수동 정책 심사 필요 |')
    out += ["", "* 점수는 검색어 일치도를 정렬한 값이며 SEO 권위 지표가 아닙니다.", ""]
    if errors:
        out += ["## 수집 오류", ""] + [f"- {x}" for x in errors]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        parser.error("SERPER_API_KEY is required")
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    leads, errors = discover(lambda query: search(query, key), registry)
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "schema": 1, "observed_at": observed, "target": "https://linkwiki.info/",
        "prospects": leads, "errors": errors
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(report_text(leads, errors, observed), encoding="utf-8")
    print(f"Found {len(leads)} candidate domains; {len(errors)} failed queries")
    for lead in leads[:15]:
        print(f"PROSPECT {lead['lead_score']:02d} {lead['domain']} {lead['url']}")
    if len(errors) == len(QUERIES):
        raise SystemExit("All search queries failed")


if __name__ == "__main__":
    main()
