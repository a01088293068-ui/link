#!/usr/bin/env python3
"""Bounded, read-only link-health observations for public LinkWiki catalog.

No login, posting, content rewriting, automatic status claims, cookies or
followed redirects. The report is intentionally private CI artifact, so
unverified data never becomes public SEO copy.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from urllib.error import HTTPError, URLError
import argparse
import ipaddress
import json
import re
import socket
import ssl

ROOT = Path(__file__).resolve().parents[1]
MAX_PER_RUN = 36
TIMEOUT = 7


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_public_host(url, resolve=socket.getaddrinfo):
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.port not in (None, 443)
            or parts.username or parts.password or parts.fragment):
        return False
    host = parts.hostname.lower()
    # IP-literal destinations are not accepted even if a test DNS resolver
    # happens to return a public address for them.
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return False
    if host in ("localhost",) or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
        return False
    try:
        ips = resolve(host, 443, type=socket.SOCK_STREAM)
        return bool(ips) and all(ipaddress.ip_address(item[4][0]).is_global
                                for item in ips)
    except (OSError, ValueError):
        return False


def daily_batch(rows, day, limit=MAX_PER_RUN):
    """Stable bounded rotation; each full catalog is sampled within six runs."""
    if not 1 <= limit <= MAX_PER_RUN:
        raise ValueError("invalid batch limit")
    if not isinstance(day, date):
        raise TypeError("day must be date")
    ordered = sorted(rows, key=lambda x: (x.get("url", ""), x.get("name", "")))
    if not ordered:
        return []
    rotation = (day.toordinal() * limit) % len(ordered)
    return (ordered[rotation:] + ordered[:rotation])[:limit]


def observe(url, checker=safe_public_host, opener=None):
    """HTTP status observation is not proof of site's safety or ownership."""
    if not checker(url):
        return {"status": "skipped_invalid_or_nonpublic", "http": None}
    client = opener or build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    req = Request(url, method="HEAD", headers={
        "User-Agent": "LinkWikiLinkHealth/1.0 (public directory maintenance)"
    })
    try:
        with client.open(req, timeout=TIMEOUT) as r:
            code = r.status
    except HTTPError as err:
        code = err.code  # redirect 3xx is *not followed*, no private network pivot
    except (URLError, OSError, TimeoutError):
        return {"status": "network_unverified", "http": None}
    if 200 <= code < 300:
        return {"status": "head_responded", "http": code}
    if 300 <= code < 400:
        return {"status": "redirect_manual_review", "http": code}
    if code in (401, 403, 405, 429):
        return {"status": "head_blocked_or_unsupported", "http": code}
    return {"status": "http_manual_review", "http": code}


def render(rows, observed, day):
    lines = ["# 링크위키 링크 접속 응답 표본 조사", "",
             "- 관측일(UTC): " + day.isoformat(),
             "- 확인 대상: " + str(len(observed)) + " / " + str(len(rows)) + " 등록 항목",
             "- HTTP HEAD 요청만 실시하고 리디렉션을 따라가지 않습니다.",
             "- 응답 확인은 공식 주소·안전성·서비스 정상 작동 여부를 보증하지 않습니다.",
             "- 403/405/429 및 타임아웃은 죽은 링크로 단정하지 않습니다.",
             "- 결과는 검토 전 사이트 공개 문구나 등급에 반영하지 않습니다.", "",
             "| 등록명 | 도메인 | HEAD 판정 | 코드 |",
             "|---|---|---|---|"]
    for item, result in observed:
        parts = urlsplit(item["url"])
        name = re.sub(r"[\r\n|]", " ", item["name"])[:80]
        lines.append("| " + name + " | " + (parts.hostname or "-") +
                     " | " + result["status"] + " | " +
                     str(result["http"] if result["http"] is not None else "-") + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", default=date.today().isoformat())
    parser.add_argument("--limit", type=int, default=MAX_PER_RUN)
    parser.add_argument("--output", default="seo/link-health-report.md")
    args = parser.parse_args()
    try:
        day = date.fromisoformat(args.day)
    except ValueError as exc:
        parser.error("invalid YYYY-MM-DD date")
    rows = json.loads((ROOT / "assets/verified-directory.json").read_text(encoding="utf-8"))
    selected = daily_batch(rows, day, args.limit)
    observations = [(item, observe(item["url"])) for item in selected]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, observations, day), encoding="utf-8")
    statuses = {}
    for _, result in observations:
        statuses[result["status"]] = statuses.get(result["status"], 0) + 1
    print("Link health sample:",len(selected),"of",len(rows),statuses,
          "report:",out)


if __name__ == "__main__":
    main()
