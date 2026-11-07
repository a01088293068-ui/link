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
PRIMARY_KEYWORDS = ("주소모음", "링크모음", "사이트모음")
SCORECARD = ROOT / "seo/core-keyword-scorecard.md"
COMPETITOR_REPORT = ROOT / "seo/core-serp-competitors.md"
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
    """Collect distinct results with their actual SERP positions.

    A short provider page is not evidence that later pages are empty.
    Position is the provider's positive ordinal when available, otherwise
    the requested page offset plus the row index, *not* the compacted list
    index after deduplication. Duplicate result URLs retain first appearance.
    """
    unique = []
    seen = set()
    for page in range(1, (limit + PAGE_SIZE - 1) // PAGE_SIZE + 1):
        batch = search(query, key, page=page)
        fresh = 0
        for index, result in enumerate(batch, 1):
            if not isinstance(result, dict):
                continue
            url = str(result.get("link", "")).strip()
            if not url or url in seen:
                continue
            raw_position = result.get("position")
            position = (raw_position if isinstance(raw_position, int)
                        and not isinstance(raw_position, bool) and raw_position > 0
                        else (page - 1) * PAGE_SIZE + index)
            # Serper occasionally returns inconsistent positions; do not
            # infer a top-30 result from an ordinal beyond our requested depth.
            if position > limit:
                continue
            seen.add(url)
            unique.append({**result, "_sample_position": position})
            fresh += 1
        if not batch or fresh == 0:
            break
    return unique


def find_result(results, domain=TARGET):
    for index, result in enumerate(results, 1):
        url = str(result.get("link") or "")
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        if host == domain or host.endswith("." + domain):
            position = result.get("_sample_position", result.get("position", index))
            if not isinstance(position, int) or isinstance(position, bool) or position < 1:
                position = index
            return {"position": position, "url": url}
    return {"position": None, "url": None}


def query_depth(query):
    return REQUESTED_RESULTS if query in CORE_KEYWORDS else LONGTAIL_RESULTS


def collect(fetch, queries=KEYWORDS):
    observations = {}
    for query in queries:
        observations[query] = find_result(fetch(query))
    return observations


def observed_competitors(results, limit=5):
    """Capture real sampled organic titles and URLs, not inferred rankings.

    Exclude LinkWiki's own host, respect result order, and never invent
    metrics such as authority scores or traffic.
    """
    competitors = []
    for position, entry in enumerate(results, 1):
        raw_url = entry.get("link")
        if not isinstance(raw_url, str):
            continue
        parts = urlsplit(raw_url)
        hostname = (parts.hostname or "").lower().removeprefix("www.")
        if parts.scheme != "https" or not hostname or hostname == TARGET or hostname.endswith("." + TARGET):
            continue
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        observed = entry.get("_sample_position", entry.get("position", position))
        if not isinstance(observed, int) or isinstance(observed, bool) or observed < 1:
            observed = position
        competitors.append({"position": observed, "title": title[:180], "url": raw_url})
        if len(competitors) >= limit:
            break
    return competitors


def competitor_report(history):
    """Summarize sampled top organic results for each primary search intent."""
    samples = sorted(history.get("samples", []), key=lambda row: row.get("date", ""))
    current = samples[-1] if samples else {}
    out = [
        "# 링크위키 핵심 키워드 검색 결과 경쟁 페이지 관찰",
        "", "측정일: " + (current.get("date") or "데이터 없음"),
        "데이터: 한국어·한국 지역 검색 API 자연 검색 표본. 검색 결과는 시점과 위치에 따라 달라질 수 있습니다.",
        "기록 대상: 주소모음·링크모음·사이트모음 각 검색 결과의 앞쪽 최대 5개 외부 페이지.",
        "광고·검색량·실제 트래픽·도메인 권위 등은 측정하지 않았습니다.",
    ]
    competitors = current.get("competitor_top", {})
    coverage = current.get("sample_coverage", {})
    counts = current.get("returned_results", {})
    for keyword in PRIMARY_KEYWORDS:
        out.extend(["", "## " + keyword, ""])
        count = counts.get(keyword)
        out.append(
            f"- 검사한 자연 검색 결과: {count}/30개 · "
            f"표본 범위: {coverage.get(keyword, '기록 없음')}"
            if isinstance(count, int) else "- 검색 표본 데이터 없음"
        )
        out.extend(["", "| 표본 순서 | 검색 결과 제목 | URL |", "|---:|---|---|"])
        rows = competitors.get(keyword, [])
        for entry in rows:
            name = str(entry["title"]).replace("|", "\\|").replace("\\n", " ")
            url = str(entry["url"]).replace("|", "%7C")
            out.append(f"| {entry['position']} | {name} | {url} |")
        if not rows:
            out.append("| - | 관측 데이터 없음 | - |")
    out.extend(["", "상위 페이지의 제목·구성·검색 의도를 실제로 확인한 뒤 "
                "링크위키의 등록 사이트 탐색 기능과 차별화할 점을 판단하세요.",
                "이 표는 자동으로 획득한 검색 제목·URL에 한정하며 "
                "다른 사이트의 콘텐츠를 복사하거나 가짜 링크를 만들기 위한 자료가 아닙니다.", ""])
    return "\n".join(out)


def coverage_for(observations, returned_results):
    """Declare whether the provider supplied the full requested SERP depth."""
    return {query: ("complete" if returned_results[query] >= query_depth(query)
                    else "partial") for query in observations}


def core_keyword_scorecard(history):
    """A factual, dated three-keyword progress report from observed SERP data.

    A partial API sample is never described as top-30 exclusion. Without
    recorded positions, performance is explicitly unknown beyond the sample.
    """
    samples = sorted(history.get("samples", []), key=lambda x: x.get("date", ""))
    latest = samples[-1] if samples else {}
    previous = samples[-2] if len(samples) >= 2 else {}
    out = [
        "# 링크위키 핵심 키워드 실측 성과표", "",
        "측정일: " + (latest.get("date") or "데이터 없음"),
        "기준: 한국 검색 API 비개인화 표본, 최대 상위 30개 자연 검색 결과", "",
        "| 키워드 | 최신 측정 | 실제 검사 범위 | 직전 측정 |",
        "|---|---|---:|---|",
    ]
    def describe(sample, keyword):
        if not sample:
            return "데이터 없음", "—"
        result = sample.get("results", {}).get(keyword, {})
        position = result.get("position")
        checked = sample.get("returned_results", {}).get(keyword)
        depth = query_depth(keyword)
        scope = (f"{checked}/{depth}" if isinstance(checked, int) else "확인 범위 기록 없음")
        if isinstance(position, int) and position > 0:
            return f"{position}위 (표본, {result.get('url') or 'URL 미기록'})", scope
        if sample.get("sample_coverage", {}).get(keyword) == "complete":
            return "검사한 상위 30개에서 미발견", scope
        return "표본 미발견 · 30위 내 여부 미확정", scope

    for keyword in PRIMARY_KEYWORDS:
        label, checked = describe(latest, keyword)
        before, _ = describe(previous, keyword)
        out.append(f"| {keyword} | {label} | {checked} | {before} |")
    out += [
        "",
        "참고: 외부 API 표본의 순위는 모든 사용자·지역의 실제 검색 순위를 대표하지 않습니다.",
        "Search Console의 노출·클릭·색인 데이터와 함께 확인해야 합니다.",
        "코드 빌드 성공, 색인 요청, 글 발행 수는 이 표의 순위 상승으로 계산하지 않습니다.",
        "",
    ]
    return "\n".join(out)


def main():
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        raise SystemExit("SERPER_API_KEY is missing")
    returned_results = {}
    competitor_top = {}
    def fetch(query):
        results = search_top_results(query, key, limit=query_depth(query))
        returned_results[query] = len(results)
        if query in PRIMARY_KEYWORDS:
            competitor_top[query] = observed_competitors(results)
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
                               "sample_coverage": coverage, "competitor_top": competitor_top})
    history["samples"] = sorted(history["samples"], key=lambda x: x["date"])[-90:]
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCORECARD.write_text(core_keyword_scorecard(history), encoding="utf-8")
    COMPETITOR_REPORT.write_text(competitor_report(history), encoding="utf-8")
    for keyword, result in observations.items():
        pos = result["position"]
        display = str(pos) if pos is not None else (
            "not found in complete sample" if coverage[keyword] == "complete"
            else "not found in partial sample; full depth unknown")
        print(f"{keyword}: {display} (checked {returned_results[keyword]} / {query_depth(keyword)} requested results)")
    print("Positions are one non-personalized API sample, not universal Google rankings.")


if __name__ == "__main__":
    main()
