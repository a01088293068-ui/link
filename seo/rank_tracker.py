#!/usr/bin/env python3
"""Observe LinkWiki appearances in an expanded fixed Korean SERP sample.

Research/measurement only; this does not change Google rankings.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "seo/rank-history.json"
TARGET = "linkwiki.info"
CORE_KEYWORDS = ("링크모음", "주소모음", "사이트모음",
                 "링크모음 사이트", "주소모음 사이트", "사이트모음 추천")
# Focused searches map to real category and guide pages, not doorway pages.
LONGTAIL_KEYWORDS = (
    "커뮤니티 사이트모음", "웹툰 링크모음", "AI 도구 사이트모음",
    "스포츠 사이트모음", "영상 사이트모음", "해외 한인 사이트모음",
    "주소모음 사이트 추천", "링크모음 사이트 추천",
    "분야별 사이트모음", "사이트 주소 확인 방법",
    "링크 접속 안됨", "사이트모음 추천 사이트",
)
KEYWORDS = CORE_KEYWORDS + LONGTAIL_KEYWORDS
# Core keywords use three SERP pages; discovery terms start with page one.
LONGTAIL_RESULTS = 10
API_URL = "https://google.serper.dev/search"
REQUESTED_RESULTS = 30
PAGE_SIZE = 10


def search(query, key, page=1):
    body = json.dumps({"q": query, "gl": "kr", "hl": "ko", "num": PAGE_SIZE, "page": page}).encode()
    request = Request(API_URL, body, {
        "X-API-KEY": key, "Content-Type": "application/json",
        "Accept": "application/json", "User-Agent": "LinkWiki-RankMonitor/1.0",
    }, method="POST")
    with urlopen(request, timeout=25) as response:
        return json.load(response).get("organic", [])


def search_top_results(query, key, limit=REQUESTED_RESULTS):
    """Gather unique organic URLs over up to three pages.

    Serper may return only 10 organic rows even when num=30 is requested.
    Stop if pagination has ended or the provider repeats a prior page.
    """
    unique = []
    seen = set()
    for page in range(1, (limit + PAGE_SIZE - 1) // PAGE_SIZE + 1):
        batch = search(query, key, page=page)
        fresh = 0
        for result in batch:
            url = str(result.get("link", "")).strip()
            if url and url not in seen:
                seen.add(url)
                unique.append(result)
                fresh += 1
        if len(batch) < PAGE_SIZE or fresh == 0:
            break
    return unique[:limit]


def find_result(results, domain=TARGET):
    for index, result in enumerate(results, 1):
        url = str(result.get("link") or "")
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        if host == domain or host.endswith("." + domain):
            return {"position": index, "url": url}
    return {"position": None, "url": None}


def query_depth(query):
    return REQUESTED_RESULTS if query in CORE_KEYWORDS else LONGTAIL_RESULTS


def collect(fetch, queries=KEYWORDS):
    observations = {}
    for query in queries:
        observations[query] = find_result(fetch(query))
    return observations


def coverage_for(observations, returned_results):
    """Declare whether the provider supplied the full requested SERP depth."""
    return {query: ("complete" if returned_results[query] >= query_depth(query)
                    else "partial") for query in observations}


def main():
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        raise SystemExit("SERPER_API_KEY is missing")
    returned_results = {}
    def fetch(query):
        results = search_top_results(query, key, limit=query_depth(query))
        returned_results[query] = len(results)
        return results
    observations = collect(fetch)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if HISTORY.exists():
        history = json.loads(HISTORY.read_text(encoding="utf-8"))
    else:
        history = {"schema": 1, "measurement": "Serper requested top 30, gl=kr, hl=ko", "samples": []}
    history["measurement"] = ("Serper paginated top 30 for core queries; top 10 for long-tail discovery, "
                              "gl=kr, hl=ko; returned_results records actual unique rows")
    day = now[:10]
    history["samples"] = [x for x in history["samples"] if x["date"] != day]
    # A missing domain in a truncated provider response is not evidence that
    # the domain lies outside the requested top-N range.
    coverage = coverage_for(observations, returned_results)
    history["samples"].append({"date": day, "observed_at": now, "results": observations,
                               "returned_results": returned_results,
                               "sample_coverage": coverage})
    history["samples"] = sorted(history["samples"], key=lambda x: x["date"])[-90:]
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for keyword, result in observations.items():
        pos = result["position"]
        display = str(pos) if pos is not None else (
            "not found in complete sample" if coverage[keyword] == "complete"
            else "not found in partial sample; full depth unknown")
        print(f"{keyword}: {display} (checked {returned_results[keyword]} / {query_depth(keyword)} requested results)")
    print("Positions are one non-personalized API sample, not universal Google rankings.")


if __name__ == "__main__":
    main()
