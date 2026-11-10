#!/usr/bin/env python3
"""Turn authenticated GSC observations into a dated, conservative SEO work queue.

This consumes the separate private Search Console artifact. It does not
request indexing, submit sitemaps, or alter public website content.
"""
import argparse
from datetime import date
import json
from pathlib import Path

SITE = "https://linkwiki.info"
PRIORITY_PATHS = ("/", "/directory", "/categories/", "/categories/search")


def decide(row, updated):
    """Separate stored Google index verdict from the recrawl freshness.

    The two signals answer different questions. A stale crawl must never
    conceal a 'Crawled - currently not indexed' Google state.
    """
    if not row:
        return ("검사 기록 없음", "재크롤링 정보 없음",
                "URL Inspection API 저장 상태 조회")
    coverage = str(row.get("coverage") or "")
    state = str(row.get("verdict") or "UNKNOWN")
    last_crawl = str(row.get("last_crawl") or "")
    lower = coverage.casefold()
    if state == "PASS":
        index_state = "색인됨"
    elif ("crawled" in lower or "크롤링됨" in coverage) and (
            "not indexed" in lower or "색인이 생성되지" in coverage):
        index_state = "크롤링 후 미색인"
    elif "unknown to google" in lower or "알려지지" in coverage:
        index_state = "Google 발견 기록 없음"
    else:
        index_state = (coverage or state or "알 수 없음")
    try:
        crawl_day = date.fromisoformat(last_crawl[:10]) if last_crawl else None
    except ValueError:
        return (index_state, "크롤링 날짜 형식 오류", "GSC 원본 날짜 검토")
    try:
        changed = date.fromisoformat(str(updated)) if updated else None
    except ValueError:
        return (index_state, "콘텐츠 변경 날짜 형식 오류", "수정 이력 검토")
    if crawl_day and changed and crawl_day < changed:
        return (index_state, "최근 변경 전 크롤링",
                "최신 버전 재크롤링 이후 색인 판정 확인; 반복적인 경미 수정 보류")
    if crawl_day and changed and crawl_day == changed:
        return (index_state, "변경일과 같은 날 · 시각 미확정",
                "변경 시각과 크롤링 시각 비교")
    if index_state == "색인됨":
        return (index_state, "변경 후 크롤링" if crawl_day and changed else
                "시각 미확정", "핵심 검색어 노출·클릭·랜딩 URL 비교")
    if index_state == "크롤링 후 미색인":
        return (index_state, "변경 후 크롤링" if crawl_day and changed else
                "시각 미확정", "콘텐츠 고유 가치·중복·사용 목적 점검; 자동 반복 제출 금지")
    if index_state == "Google 발견 기록 없음":
        return (index_state, "미발견/시각 없음",
                "내부 링크·사이트맵·HTTP 접근성 점검")
    return (index_state, "시각 미확정" if not crawl_day else "변경 이후 크롤링",
            "GSC robots·canonical·Google 선택 URL 비교")


def render(snapshot):
    changes = snapshot.get("significant_page_updates") or {}
    inspected = {str(r.get("url")): r for r in snapshot.get("inspections") or []}
    lines = [
        "# 링크위키 Google 색인 및 핵심 키워드 실측 우선조치표", "",
        "- GSC 데이터 종료일: " + str(snapshot.get("end_date") or "정보 없음"),
        "- 이 표는 Google에 저장된 URL 검사 결과이며 현재 공개 HTML이나 실시간 순위가 아닙니다.",
        "- Google의 재크롤링 이전에는 최신 편집 효과를 판단할 수 없습니다.", "",
        "## 중요 URL", "",
        "| URL | 마지막 중요한 수정 | Google 마지막 크롤링 | 색인 저장 상태 | 수정 후 재크롤링 | 우선 조치 |",
        "|---|---|---|---|---|---|",
    ]
    for path in PRIORITY_PATHS:
        url = SITE + path
        row = inspected.get(url)
        changed = changes.get(path, "")
        status, freshness, action = decide(row, changed)
        crawled = str((row or {}).get("last_crawl") or "-")
        values = (url, changed or "-", crawled, status, freshness, action)
        lines.append("| " + " | ".join(str(v).replace("|", "%7C").replace("\n", " ") for v in values) + " |")
    lines.extend(["", "## 정확 검색어 (브랜드·연관 검색어 제외)", "",
                  "| 검색어 | GSC 공개 노출 | 클릭 | 평균 순위 | 실제 노출 URL |",
                  "|---|---:|---:|---:|---|"])
    keywords = {r.get("keyword"): r for r in snapshot.get("core_keywords") or []}
    for key in ("주소모음", "링크모음", "사이트모음"):
        row = keywords.get(key) or {}
        if row.get("observed"):
            pages = ", ".join(row.get("pages") or []) or "페이지 쌍 비공개"
            cells = (key, row.get("impressions", 0), row.get("clicks", 0),
                     row.get("position") if row.get("position") is not None else "-",
                     pages)
        else:
            cells = (key, "미관측", "-", "-", "검색어 비공개 가능")
        lines.append("| " + " | ".join(str(v).replace("|", "%7C") for v in cells) + " |")
    lines.extend([
        "", "## 한국 이용자 기준 정확 검색어 7일 성과", "",
        "- Google Search Console 국가 필터 대한민국(kor) 적용. "
        "위 전 세계 합산 순위와 혼동하지 않습니다.",
        "- GSC 검색어 익명화로 '관측 없음'은 노출이 정확히 0회라는 뜻이 아닙니다.",
        "| 키워드 | 직전 7일 노출 / 클릭 / 순위 | 최근 7일 노출 / 클릭 / 순위 |",
        "|---|---|---|",
    ])
    korea_error = snapshot.get("korea_core_weekly_error")
    if korea_error:
        lines.append("| 한국 GSC 조회 오류 | " + str(korea_error) + " | - |")
    else:
        weekly = {r.get("keyword"): r for r in snapshot.get("korea_core_weekly") or []}
        for key in ("주소모음", "링크모음", "사이트모음"):
            item = weekly.get(key) or {}
            def fmt(v):
                if not v or not v.get("observed"):
                    return "관측 없음"
                position = v.get("position")
                return (str(v.get("impressions", 0)) + " / " +
                        str(v.get("clicks", 0)) + " / " +
                        (str(position) if position is not None else "-"))
            lines.append("| " + key + " | " + fmt(item.get("previous")) +
                         " | " + fmt(item.get("recent")) + " |")
    lines.append("")
    for error_key, label in (("core_query_error", "핵심 검색어"), ("inspection_error", "URL 검사"),
                             ("sitemap_error", "사이트맵")):
        if snapshot.get(error_key):
            lines.append("- " + label + " API 조회 오류: " + str(snapshot[error_key]))
    lines.extend(["", "## 순위 목표의 작업 기준", "",
                  "1. 새로운 Google 크롤링 날짜가 기록되기 전에는 배포 성공을 색인 성공으로 간주하지 않습니다.",
                  "2. 핵심 검색어 세 개의 평균 순위는 실제 노출 관측이 있을 때만 기록합니다.",
                  "3. 미색인 URL이 새로 크롤링된 후에도 미색인이면 복제 문구가 아닌 기능·정보 가치를 개선합니다.",
                  "4. 보이는 백링크 수·사이트 등록 수·사이트맵 제출만으로 순위 상승을 주장하지 않습니다.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("seo/search-console-snapshot.json"))
    parser.add_argument("--output", type=Path, default=Path("seo/index-priority-plan.md"))
    args = parser.parse_args()
    snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    if snapshot.get("schema") != 1:
        parser.error("unsupported Search Console snapshot schema")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(snapshot), encoding="utf-8")
    print("Wrote", args.output)


if __name__ == "__main__":
    main()
