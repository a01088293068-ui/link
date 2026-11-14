#!/usr/bin/env python3
"""Compare private GSC snapshots from two completed workflow artifacts.

The report only compares Google's saved inspection data and public query rows.
No API call requests indexing and no private GSC data is committed to Git.
"""
import argparse
from datetime import date
import io
import json
import os
from pathlib import Path
import re
import zipfile

TARGETS = (
    "https://linkwiki.info/",
    "https://linkwiki.info/directory",
    "https://linkwiki.info/categories/",
    "https://linkwiki.info/categories/ai",
    "https://linkwiki.info/categories/sports",
    "https://linkwiki.info/categories/search",
    "https://linkwiki.info/categories/finance",
    "https://linkwiki.info/categories/education",
    "https://linkwiki.info/categories/news",
    "https://linkwiki.info/categories/shopping",
    "https://linkwiki.info/categories/travel",
    "https://linkwiki.info/guides/address-check",
)
KEYWORDS = ("주소모음", "링크모음", "사이트모음")


def _table_cell(value):
    return str(value if value is not None else "-").replace("|", "%7C").replace("\n", " ")


def _inspect(snapshot, url):
    return next((row for row in snapshot.get("inspections", []) or []
                 if row.get("url") == url), None)


def _inspect_label(row):
    if not row:
        return "검사 자료 없음"
    return (str(row.get("verdict") or "UNKNOWN") + " / " +
            str(row.get("coverage") or "판정 설명 없음"))


def render(current, previous=None, prior_run_url="", reason=""):
    """Do not turn anonymized GSC query rows or old URL copies into rank claims."""
    if current.get("schema") != 1:
        raise ValueError("unsupported current GSC snapshot schema")
    lines = [
        "# Google 색인 재크롤링 및 한국 핵심 키워드 전회 대비 변화", "",
        "- 현재 GSC 집계 종료일: " + str(current.get("end_date") or "미제공"),
        "- 이 보고서는 Google에 저장된 URL 검사 결과와 GSC에 공개된 검색어 행만 비교합니다.",
        "- 동일 날짜 재검사는 순위 향상 증거가 아니며, 저장된 크롤링 시간은 실제 배포 완료를 뜻하지 않습니다.",
        "- 검색어 미관측은 GSC 익명화 때문일 수 있어 실제 노출 0회를 보장하지 않습니다.",
    ]
    if not previous:
        lines += ["", "## 이전 자료 비교 불가", "",
                  "직전 정상 실행의 비공개 Search Console 아티팩트를 불러오지 못했습니다.",
                  "원인: " + (reason or "이전 아티팩트가 없음"), "",
                  "신규 데이터 자체는 같은 실행의 index-priority-plan.md에서 확인하세요.", ""]
        return "\n".join(lines)
    if previous.get("schema") != 1:
        raise ValueError("unsupported previous GSC snapshot schema")
    lines += [
        "- 이전 GSC 집계 종료일: " + str(previous.get("end_date") or "미제공"),
        ("- 이전 정상 보고서: " + prior_run_url if prior_run_url else
         "- 이전 정상 보고서: 아티팩트 내부 원본"), "",
        "## 핵심 URL의 색인·크롤링 기록 비교", "",
        "| URL | 이전 저장 색인 판정 | 현재 저장 색인 판정 | 이전 크롤링 | 현재 크롤링 | 판단 |",
        "|---|---|---|---|---|---|",
    ]
    for url in TARGETS:
        before, after = _inspect(previous, url), _inspect(current, url)
        before_crawl = (before or {}).get("last_crawl") or "-"
        after_crawl = (after or {}).get("last_crawl") or "-"
        before_label, after_label = _inspect_label(before), _inspect_label(after)
        if not before or not after:
            change = "검사 대상 누락 · 결론 불가"
        elif after_crawl != before_crawl and after_crawl != "-":
            change = "저장 크롤링 시각 갱신"
            if before_crawl != "-" and after_crawl < before_crawl:
                change = "기록된 크롤링 날짜 역행 · 원본 확인"
        elif before_label != after_label:
            change = "색인 판정 변화 · 크롤링 시간 동일/불명"
        else:
            change = "새로운 크롤링 증거 없음"
        if before and after and before.get("verdict") != after.get("verdict"):
            change += " · 색인 verdict 변경"
        lines.append("| " + " | ".join(map(_table_cell, (
            url, before_label, after_label, before_crawl, after_crawl, change,
        ))) + " |")

    lines += ["", "## 대한민국 이용자 기준 핵심 키워드 GSC 관측", "",
              "| 검색어 | 이전 최근 7일 | 현재 최근 7일 | 비교 가능 여부 |",
              "|---|---|---|---|"]
    def recent(snapshot, keyword):
        entry = next((row for row in snapshot.get("korea_core_weekly", []) or []
                      if row.get("keyword") == keyword), {})
        return entry.get("recent") or {}
    same_window = (current.get("end_date") == previous.get("end_date"))
    # Search Console's rolling 7-day windows overlap when compared daily.
    # Shared days mean differences are NOT independent week-over-week growth.
    try:
        current_end = date.fromisoformat(str(current["end_date"]))
        prior_end = date.fromisoformat(str(previous["end_date"]))
        days_apart = (current_end - prior_end).days
    except (ValueError, KeyError, TypeError):
        days_apart = None
    for key in KEYWORDS:
        past, now = recent(previous, key), recent(current, key)
        def display(row):
            if not row.get("observed"):
                return "관측 없음"
            return (str(row.get("impressions", 0)) + " 노출 / " +
                    str(row.get("clicks", 0)) + " 클릭 / " +
                    (str(row["position"]) + "위" if row.get("position") is not None
                     else "평균 순위 없음"))
        if current.get("korea_core_weekly_error") or previous.get("korea_core_weekly_error"):
            status = "국가 필터 API 오류로 비교 불가"
        elif same_window:
            status = "동일 집계 종료일 · 성과 추세 판정 불가"
        elif days_apart is None or days_apart < 0:
            status = "집계 날짜 누락/역행 · 비교 불가"
        elif 0 < days_apart < 7:
            status = f"최근 7일 구간 {7-days_apart}일 중복 · 독립 기간 대비 아님"
        elif not past.get("observed") and not now.get("observed"):
            status = "양쪽 모두 미관측 · 변화 판정 불가"
        else:
            status = "종료일이 다른 7일 구간 · 표본 규모 유의"
        lines.append("| " + " | ".join(map(_table_cell, (
            key, display(past), display(now), status,
        ))) + " |")
    lines += ["",
              "- 7일 성과를 하루 간격으로 비교할 때 같은 날짜가 6일 겹칩니다. 따라서 노출/평균순위 차이는 독립적인 주간 성과 개선으로 해석하지 않습니다.",
              ""]
    lines += ["",
              "## 이 보고서의 판단 기준", "",
              "1. Googlebot 재크롤링 시각 갱신이 색인 성공이나 순위 상승을 뜻하지는 않습니다.",
              "2. Google verdict PASS 확인 없이 미색인 해소를 주장하지 않습니다.",
              "3. 검색 노출은 한국 국가 필터·정확 일치 검색어 기준으로만 비교합니다.",
              "4. 1~3위 진입은 실제 표본에서 확인될 때만 기록합니다.", ""]
    return "\n".join(lines)


def prior_snapshot(session, repo, current_run):
    """Read the newest OTHER successful private artifact; never expose secrets."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid GITHUB_REPOSITORY")
    url = "https://api.github.com/repos/" + repo + "/actions/artifacts"
    response = session.get(url, params={"name": "search-console-performance",
                                         "per_page": 40}, timeout=25)
    response.raise_for_status()
    artifacts = response.json().get("artifacts", [])
    eligible = [a for a in artifacts if
                a.get("name") == "search-console-performance" and
                not a.get("expired", False) and
                isinstance(a.get("workflow_run", {}).get("id"), int) and
                a.get("workflow_run", {}).get("id") < current_run]
    eligible.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    errors = []
    for artifact in eligible[:5]:
        try:
            if int(artifact.get("size_in_bytes", 0)) > 2000000:
                continue
            res = session.get(artifact["archive_download_url"], timeout=35)
            res.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(res.content)) as archive:
                if "search-console-snapshot.json" not in archive.namelist():
                    continue
                data = json.loads(archive.read("search-console-snapshot.json"))
            if data.get("schema") != 1:
                continue
            run_id = artifact.get("workflow_run", {}).get("id")
            return data, ("https://github.com/" + repo +
                          "/actions/runs/" + str(run_id)), ""
        except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
            errors.append(type(error).__name__)
        except Exception as error:
            # An expired or temporarily inaccessible artifact should not make
            # the current authenticated GSC measurement disappear.
            errors.append(type(error).__name__)
    return None, "", ("직전 호환 아티팩트 없음" if not errors else
                      "직전 아티팩트 다운로드·형식 오류: " + ", ".join(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path,
                        default=Path("seo/search-console-snapshot.json"))
    parser.add_argument("--output", type=Path,
                        default=Path("seo/search-console-delta.md"))
    args = parser.parse_args()
    current = json.loads(args.current.read_text(encoding="utf-8"))
    previous, prior_url, reason = None, "", "GitHub 토큰이나 실행 식별자 없음"
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if token and repo and run_id:
        import requests
        session = requests.Session()
        session.headers.update({
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            previous, prior_url, reason = prior_snapshot(session, repo, int(run_id))
        except Exception as error:
            reason = "기존 아티팩트 조회 실패: " + type(error).__name__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(current, previous, prior_url, reason),
                           encoding="utf-8")
    print("Wrote private GSC comparison:", args.output)


if __name__ == "__main__":
    main()
