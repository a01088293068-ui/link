#!/usr/bin/env python3
"""LinkWiki backlink ledger, deduplication and public-link health audits.

No registrations are sent to third-party sites. Submission integrations require
platform-specific permission/API contracts; this program never bypasses forms.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "seo" / "backlink-registry.json"
REPORT = ROOT / "seo" / "backlink-status.md"
USER_AGENT = "LinkWiki-LinkAudit/1.0 (+https://linkwiki.info/)"
MAX_HTML_BYTES = 1_000_000


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_url(raw, *, allow_blank=False):
    value = str(raw or "").strip()
    if not value and allow_blank:
        return ""
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"HTTPS public URL required: {value!r}")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal")):
        raise ValueError("Private hosts are not permitted")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not ip.is_global:
            raise ValueError("Non-public IP is not permitted")
    return value


def key_for(platform, submit_url):
    return hashlib.sha256((platform.lower().strip() + "\n" + submit_url.lower().rstrip("/")).encode()).hexdigest()[:16]


def load_registry(path):
    if not path.exists():
        return {"schema": 1, "target_domain": "linkwiki.info", "entries": []}
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("schema") != 1 or not isinstance(result.get("entries"), list):
        raise ValueError("Unrecognized registry schema")
    return result


def save_registry(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def import_csv(registry, filename):
    with open(filename, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"platform", "submission_url", "public_url", "submission_status"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("CSV headers required: platform,submission_url,public_url,submission_status")
        rows = list(reader)
    known = {entry["id"]: entry for entry in registry["entries"]}
    new_count = updated = 0
    for index, row in enumerate(rows, 2):
        platform = str(row["platform"] or "").strip()
        if not platform:
            raise ValueError(f"Row {index}: missing platform")
        submission_url = validate_url(row["submission_url"])
        public_url = validate_url(row.get("public_url"), allow_blank=True)
        status = str(row["submission_status"] or "").strip().lower()
        if status not in {"not_submitted", "submitted", "pending_review", "approved", "rejected", "unknown"}:
            raise ValueError(f"Row {index}: invalid submission_status {status!r}")
        entry_id = key_for(platform, submission_url)
        if entry_id in known:
            entry = known[entry_id]
            # Never replace a known live URL with blank CSV input or downgrade
            # approval to unknown during re-import.
            if public_url and public_url != entry.get("public_url"):
                entry["public_url"] = public_url
                entry["last_checked"] = ""
            if status != "unknown":
                entry["submission_status"] = status
            if row.get("notes"):
                entry["notes"] = str(row["notes"])[:500]
            updated += 1
        else:
            entry = {"id": entry_id, "platform": platform, "submission_url": submission_url,
                     "public_url": public_url, "submission_status": status,
                     "audit_status": "unverified", "last_checked": "", "http_status": None,
                     "link_found": False, "rel": [], "noindex": None,
                     "notes": str(row.get("notes") or "")[:500]}
            registry["entries"].append(entry)
            known[entry_id] = entry
            new_count += 1
    registry["entries"].sort(key=lambda x: (x["platform"].lower(), x["id"]))
    return new_count, updated


class LinkParser(HTMLParser):
    def __init__(self, domain):
        super().__init__(convert_charrefs=True)
        self.domain = domain.lower().removeprefix("www.")
        self.matches = []
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        info = dict(attrs)
        if tag == "meta" and str(info.get("name", "")).lower() in {"robots", "googlebot"}:
            directives = str(info.get("content", "")).lower()
            self.noindex |= "noindex" in directives
        if tag != "a":
            return
        href = str(info.get("href") or "")
        try:
            host = urllib.parse.urlsplit(href).hostname
        except ValueError:
            return
        if host and host.lower().removeprefix("www.") == self.domain:
            rel = str(info.get("rel") or "").lower().split()
            self.matches.append(sorted(set(rel)))


class SafeRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        validate_url(newurl)
        validate_dns(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def validate_dns(target):
    hostname = urllib.parse.urlsplit(target).hostname
    for _, _, _, _, address in socket.getaddrinfo(hostname, 443):
        if not ipaddress.ip_address(address[0]).is_global:
            raise ValueError("Host resolved to non-public address")


def fetch_public(url):
    """Read limited HTML with explicit timeout; never submit a form."""
    validate_url(url)
    # Re-resolve host to reject common internal-address SSRF targets.
    validate_dns(url)
    opener = urllib.request.build_opener(SafeRedirects)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with opener.open(request, timeout=15) as response:
        validate_dns(response.geturl())
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        xrobots = response.headers.get("X-Robots-Tag", "")
        if "html" not in content_type.lower():
            return status, "", xrobots, content_type
        raw = response.read(MAX_HTML_BYTES + 1)
        if len(raw) > MAX_HTML_BYTES:
            raise ValueError("HTML too large")
        encoding = response.headers.get_content_charset() or "utf-8"
        return status, raw.decode(encoding, "replace"), xrobots, content_type


def evaluate_html(source, domain, xrobots=""):
    parser = LinkParser(domain)
    parser.feed(source)
    has_link = bool(parser.matches)
    noindex = parser.noindex or bool(re.search(r"\bnoindex\b", xrobots.lower()))
    rels = sorted({item for match in parser.matches for item in match})
    if not has_link:
        result = "missing_link"
    elif noindex:
        result = "noindex"
    elif any(word in rels for word in ("nofollow", "ugc", "sponsored")):
        result = "link_with_rel"
    else:
        result = "verified_link"
    return result, has_link, rels, noindex


def audit(registry, limit=30):
    entries = [item for item in registry["entries"] if item.get("public_url")]
    entries.sort(key=lambda x: (x.get("last_checked", ""), x["id"]))
    tested = 0
    for entry in entries[:limit]:
        try:
            status, body, xrobots, content_type = fetch_public(entry["public_url"])
            if not body:
                entry.update(audit_status="not_html", http_status=status,
                             link_found=False, rel=[], noindex=None)
            else:
                result, found, rels, noindex = evaluate_html(body, registry["target_domain"], xrobots)
                entry.update(audit_status=result, http_status=status,
                             link_found=found, rel=rels, noindex=noindex)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            entry.update(audit_status="fetch_error", http_status=getattr(exc, "code", None),
                         link_found=False, rel=[], noindex=None,
                         last_error=f"{type(exc).__name__}: {str(exc)[:150]}")
        entry["last_checked"] = utc_now()
        tested += 1
    return tested


def markdown_report(registry):
    entries = registry["entries"]
    totals = {}
    for entry in entries:
        key = entry.get("audit_status", "unverified")
        totals[key] = totals.get(key, 0) + 1
    out = ["# 링크위키 백링크 현황", "", f"기록 시각: {utc_now()} (UTC)",
           f"대상: {registry['target_domain']}", f"등록처: {len(entries)}개", "",
           "## 공개 링크 검증 상태", ""]
    out.extend(f"- {key}: {value}" for key, value in sorted(totals.items()))
    out += ["", "상태가 `verified_link`여도 SEO 순위 상승이나 색인을 보장하지 않습니다.",
            "`link_with_rel`은 nofollow/ugc/sponsored 중 하나가 포함된 실제 링크입니다.",
            "자바스크립트로 삽입되는 링크는 이 정적 HTML 검출기에 잡히지 않을 수 있습니다.", "",
            "## 등록처별 상세", "", "| 등록처 | 제출 | 검사 | 마지막 확인 | 공개 URL |", "|---|---|---|---|---|"]
    for entry in entries:
        name = entry["platform"].replace("|", "\\|")
        url = entry.get("public_url", "")
        safe_url = url.replace("|", "%7C")
        out.append(f"| {name} | {entry['submission_status']} | {entry['audit_status']} | {entry['last_checked'][:10]} | {safe_url} |")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["import", "audit", "report", "list"])
    parser.add_argument("--file", help="CSV with registration records (for import)")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    registry = load_registry(args.registry)
    if args.command == "import":
        if not args.file:
            parser.error("import requires --file")
        new, updated = import_csv(registry, args.file)
        save_registry(args.registry, registry)
        print(f"Imported: {new} new, {updated} existing, {len(registry['entries'])} total")
    elif args.command == "audit":
        if not 1 <= args.limit <= 200:
            parser.error("--limit must be between 1 and 200")
        count = audit(registry, args.limit)
        save_registry(args.registry, registry)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown_report(registry), encoding="utf-8")
        print(f"Audited {count} public URL(s); report: {args.report}")
    elif args.command == "report":
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown_report(registry), encoding="utf-8")
        print(f"Wrote {args.report}")
    else:
        for item in registry["entries"]:
            print(f"{item['platform']}: {item['submission_status']} / {item['audit_status']} / {item['public_url']}")


if __name__ == "__main__":
    main()
