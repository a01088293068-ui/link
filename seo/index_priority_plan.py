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
PRIORITY_PATHS = (
    "/", "/directory", "/categories/",
    "/categories/search", "/categories/community", "/categories/ai",
    "/categories/sports", "/categories/video", "/categories/webtoon",
    "/categories/comics-directory", "/categories/korean",
)


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
                "수정 시각과 크롤링 시각 비교")
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


def historic_canonical_mismatches(inspections):
    """Report stale .html canonicals without claiming the live site is broken."""
    items = []
    for row in inspections or []:
        url = str(row.get("url") or "")
        declared = str(row.get("user_canonical") or "")
        chosen = str(row.get("google_canonical") or "")
        if not url.startswith(SITE + "/") or not declared or not chosen:
            continue
        if declared != chosen:
            items.append((url, declared, chosen, str(row.get("last_crawl") or "-")))
    return items


def sitemap_diagnostic(sitemaps, error=""):
    """Use the GSC submitted sitemap state, not the public XML response."""
    target = SITE + "/sitemap.xml"
    legacy = SITE + "/sitemap-v2.xml"
    items = {str(item.get("path") or ""): item for item in sitemaps or []}
    lines = ["", "## Google에 제출된 사이트맵 상태", ""]
    if error:
        lines.append("- 사이트맵 API 오류: " + str(error))
        return lines
    for url in (target, legacy):
        item = items.get(url)
        if not item:
            lines.append("- " + url + ": 제출 기록 미관측")
            continue
        downloaded = str(item.get("lastDownloaded") or "기록 없음")
        pending = bool(item.get("isPending"))
        errors = int(item.get("errors") or 0)
        lines.append("- " + url + ": 마지막 Google 다운로드 " + downloaded
                     + "; 처리 대기 " + ("예" if pending else "아니오")
                     + "; 처리 오류 " + str(errors))
        if url == target and (pending or downloaded == "기록 없음"):
            lines.append("- 기본 사이트맵은 Google 처리 완료가 아직 확인되지 않습니다. "
                         "공개 XML 정상 응답을 Google 다운로드 성공으로 간주하지 마세요.")
    return lines


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
    # Article diagnostics are evidence-based: list only URLs actually
    # returned by Google's stored inspection API, not all build artifacts.
    article_rows = sorted(
        (row for row in snapshot.get("inspections") or []
         if isinstance(row, dict)
         and str(row.get("url") or "").startswith(SITE + "/blog/")
         and str(row.get("url") or "").endswith("/")),
        key=lambda row: str(row.get("url") or ""),
    )
    lines.extend(["", "## 핵심 가이드의 Google 저장 색인 상태", "",
                  "- URL Inspection API로 실제 조회된 글만 표시합니다. "
                  "표의 부재는 색인 실패나 노출 0회를 뜻하지 않습니다."])
    if not article_rows:
        lines.append("- 검사된 블로그 가이드 URL 없음")
    else:
        lines.extend(["", "| 가이드 URL | Google 저장 색인 상태 | 마지막 크롤링 | 우선 조치 |",
                      "|---|---|---|---|"])
        for row in article_rows:
            url = str(row["url"])
            state, freshness, action = decide(row, "")
            if state == "색인됨":
                action = "검색어별 실제 노출 URL과 클릭·순위 추적"
            elif state == "크롤링 후 미색인":
                action = "글의 독립적인 검색 목적과 원문 가치 확인; 중복 글 양산 금지"
            elif state == "Google 발견 기록 없음":
                action = "사이트맵·디렉터리 유입 링크·HTTP 응답 검사"
            else:
                action = "Google 저장 상태와 canonical 확인"
            cells = (url, state, row.get("last_crawl") or "-", action)
            lines.append("| " + " | ".join(
                str(v).replace("|", "%7C").replace("\\n", " ") for v in cells) + " |")

    mismatches = historic_canonical_mismatches(snapshot.get("inspections"))
    lines.extend(["", "## Google 저장본 Canonical 차이", ""])
    if mismatches:
        lines.append("- 아래는 과거 Google 크롤링에 저장된 대표 URL입니다. "
                     "최신 배포본의 문제라고 단정할 수 없습니다.")
        lines.extend(["", "| 검사 URL | 사이트 선언 URL | Google 선택 URL | 마지막 크롤링 |",
                      "|---|---|---|---|"])
        for values in mismatches:
            lines.append("| " + " | ".join(
                str(v).replace("|", "%7C") for v in values) + " |")
        lines.append("- 우선조치: 최신 HTML의 canonical과 Google 재크롤링 이후 저장본을 비교하세요. "
                     "확인 없이 기존 URL을 일괄 리디렉션하지 마세요.")
    else:
        lines.append("- 조회한 URL에서 명시적 canonical 불일치 기록 없음 "
                     "(조회되지 않은 URL은 판단 불가).")
    lines.extend(sitemap_diagnostic(snapshot.get("sitemaps"),
                                    snapshot.get("sitemap_error") or ""))

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
