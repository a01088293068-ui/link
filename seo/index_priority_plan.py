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
    """Return factual crawl/index state and a single next action."""
    if not row:
        return ("검사 기록 없음", "URL Inspection API의 저장 상태 확인")
    coverage = str(row.get("coverage") or "")
    state = str(row.get("verdict") or "UNKNOWN")
    last_crawl = str(row.get("last_crawl") or "")
    crawl_day = None
    try:
        if last_crawl:
            crawl_day = date.fromisoformat(last_crawl[:10])
    except ValueError:
        return ("크롤링 날짜 오류", "GSC 원본 날짜 형식 확인")
    try:
        changed = date.fromisoformat(str(updated)) if updated else None
    except ValueError:
        return ("콘텐츠 변경일 오류", "변경 이력 원본 확인")
    if crawl_day and changed and crawl_day < changed:
        return ("최신 변경 전 크롤링", "Google 재크롤링 이후 색인 결과 확인; 동일 페이지 반복 수정 보류")
    if crawl_day and changed and crawl_day == changed:
        return ("같은 날짜 크롤링 · 시점 미확정", "실제 수정 시각과 크롤링 시각 비교; 순위 변화 단정 금지")
    if state == "PASS":
        return ("색인됨" if crawl_day else "색인됨 · 크롤링 시각 미제공",
                "정확 검색어 노출·클릭·검색 의도 비교")
    lower = coverage.casefold()
    if ("crawled" in lower or "크롤링됨" in coverage) and (
        "not indexed" in lower or "색인이 생성되지" in coverage):
        return ("크롤링 후 미색인", "콘텐츠 고유 가치·검색 의도 적합성 검토; 자동 재제출 금지")
    if "unknown to google" in lower or "알려지지" in coverage:
        return ("Google 발견 기록 없음", "내부 링크·사이트맵·URL 접근성의 실제 증거 확인")
    if not crawl_day:
        return ("크롤링 시점 불명", "색인 데이터와 현재 HTTP 응답을 분리해 점검")
    return ("추가 확인 필요", "GSC 저장 상태의 색인 허용·robots·canonical 검사")


def render(snapshot):
    changes = snapshot.get("significant_page_updates") or {}
    inspected = {str(r.get("url")): r for r in snapshot.get("inspections") or []}
    lines = [
        "# 링크위키 Google 색인 및 핵심 키워드 실측 우선조치표", "",
        "- GSC 데이터 종료일: " + str(snapshot.get("end_date") or "정보 없음"),
        "- 이 표는 Google에 저장된 URL 검사 결과이며 현재 공개 HTML이나 실시간 순위가 아닙니다.",
        "- Google의 재크롤링 이전에는 최신 편집 효과를 판단할 수 없습니다.", "",
        "## 중요 URL", "",
        "| URL | 마지막 중요한 수정 | Google 마지막 크롤링 | 상태 | 우선 조치 |",
        "|---|---|---|---|---|",
    ]
    for path in PRIORITY_PATHS:
        url = SITE + path
        row = inspected.get(url)
        changed = changes.get(path, "")
        status, action = decide(row, changed)
        crawled = str((row or {}).get("last_crawl") or "-")
        values = (url, changed or "-", crawled, status, action)
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
