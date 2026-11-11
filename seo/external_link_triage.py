#!/usr/bin/env python3
"""Turn actual read-only HTTP observations into an actionable editorial review.

No site is labeled dead or verified by a single HEAD observation.
Only exact entries from the source catalog are accepted; outputs are private
CI artifacts, never published as site-level endorsements or safety badges.
"""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

from observe_external_links import DATA

ACTIONS = {
    "http_responded": ("관찰 기록", "HTTP 응답은 확인됐으나 실제 화면·공식성·안전성은 미확인"),
    "redirect_review": ("목적지 수동 확인", "HTTPS 최종 도착 주소·운영 주체를 확인하고 필요 시 등록 URL 수정"),
    "access_limited": ("GET 방식 수동 확인", "HEAD 요청 차단·봇 제한 가능성 확인; 자동 삭제 금지"),
    "http_error_review": ("브라우저 재확인", "GET으로 실제 접속과 공식 링크를 대조하고 지속 오류일 때만 수정 검토"),
    "network_uncertain": ("시간차 재확인", "일시적 네트워크 문제 가능성. 원인 단정하지 않음"),
    "unexpected_response": ("상태 코드 검토", "예상 밖 응답. 실제 웹사이트와 비교 필요"),
}
PRIORITY = ("http_error_review", "redirect_review", "access_limited",
            "network_uncertain", "unexpected_response", "http_responded")


def markdown_cell(value):
    return str(value).replace("|", "∣").replace("\n", " ").replace("\r", " ").strip()


def validate_report(snapshot, records):
    if not isinstance(snapshot, dict):
        raise ValueError("invalid observation payload")
    try:
        date.fromisoformat(snapshot["date_utc"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("invalid observation date") from exc
    rows = snapshot.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("no real observations")
    if snapshot.get("checked_count") != len(rows):
        raise ValueError("observation count mismatch")
    by_url = {record["url"]: record for record in records}
    if len(by_url) != len(records):
        raise ValueError("duplicate catalog URLs")
    seen = set()
    for entry in rows:
        if not isinstance(entry, dict) or entry.get("url") not in by_url:
            raise ValueError("observed URL not in published catalog")
        url = entry["url"]
        if url in seen:
            raise ValueError("duplicate observed URL")
        seen.add(url)
        record = by_url[url]
        if (entry.get("name") != record["name"] or
                entry.get("category") != record["category"]):
            raise ValueError("observation record differs from catalog")
        observation = entry.get("observation")
        if not isinstance(observation, dict):
            raise ValueError("missing observation metadata")
        status = observation.get("status")
        if status not in ACTIONS:
            raise ValueError("unsupported observation status")
        code = observation.get("http_code")
        if code is not None and (not isinstance(code, int) or isinstance(code, bool)
                                 or not 100 <= code <= 599):
            raise ValueError("invalid HTTP status")
    return rows


def render(snapshot, records):
    rows = validate_report(snapshot, records)
    counts = Counter(item["observation"]["status"] for item in rows)
    out = [
        "# 링크위키 외부 링크 상태 검토 보고서",
        "",
        f"- 점검 날짜(UTC): {snapshot['date_utc']}",
        f"- 등록 데이터: {len(records)}개 중 {len(rows)}개 관찰",
        "- 방식: 인증 없는 공개 URL에 HEAD 요청 (리디렉션 자동 추적 안 함)",
        "- 주의: HEAD 응답은 실사용 가능, 공식 소유권, 안전 여부의 증거가 아닙니다.",
        "- 처리 원칙: 한 번의 관찰만으로 링크를 삭제하거나 수정하지 않습니다.",
        "",
        "## HTTP 관찰 분포",
        "",
        "| 분류 | 개수 | 의미 |",
        "|---|---:|---|",
    ]
    for code in PRIORITY:
        out.append(f"| {code} | {counts[code]} | {ACTIONS[code][1]} |")
    out += ["", "## 운영자 재확인 대기 항목", "",
            "| 서비스 | 등록 URL | 응답 | 후속 작업 |",
            "|---|---|---|---|"]
    pending = [item for item in rows
               if item["observation"]["status"] != "http_responded"]
    pending.sort(key=lambda item: (PRIORITY.index(item["observation"]["status"]),
                                   item["name"]))
    for item in pending:
        observation = item["observation"]
        label = observation.get("http_code", observation["status"])
        action = ACTIONS[observation["status"]][0]
        out.append(
            f"| {markdown_cell(item['name'])} | {markdown_cell(item['url'])} "
            f"| {markdown_cell(label)} | {action} |"
        )
    if not pending:
        out.append("| (없음) | — | — | — |")
    out += ["", "## HTTP 응답 관찰 목록 (미검증)", "",
            "| 서비스 | HTTP | 등록 URL |",
            "|---|---:|---|"]
    for item in rows:
        if item["observation"]["status"] != "http_responded":
            continue
        out.append(f"| {markdown_cell(item['name'])} "
                   f"| {item['observation'].get('http_code', '—')} "
                   f"| {markdown_cell(item['url'])} |")
    out += ["", "## 다음 처리 기준", "",
            "1. 404·405는 HEAD 전용 응답일 수 있으므로 로그인 없이 브라우저 GET으로 확인합니다.",
            "2. 301·302·307·308은 최종 HTTPS 도착지와 공식 운영 안내를 확인합니다.",
            "3. 403·429는 자동 요청 제한일 수 있으므로 우회하거나 반복 요청하지 않습니다.",
            "4. 실제로 잘못된 등록 주소가 확인되면 공식 URL 근거를 첨부해 별도 수정합니다.",
            "5. 결과는 운영 검토용 비공개 아티팩트로 보관하며, 사용자에게 검증 배지를 표시하지 않습니다.",
            ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path,
                        default=Path(__file__).resolve().parent / "external-link-observations.json")
    parser.add_argument("--catalog", type=Path, default=DATA)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "external-link-review.md")
    args = parser.parse_args()
    snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    records = json.loads(args.catalog.read_text(encoding="utf-8"))
    report = render(snapshot, records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    pending = sum(row["observation"]["status"] != "http_responded"
                  for row in snapshot["results"])
    print(f"REVIEW_REPORT_CREATED: {len(snapshot['results'])} observations, {pending} awaiting review")
    print("No catalog links modified or removed.")


if __name__ == "__main__":
    main()
