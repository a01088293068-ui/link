#!/usr/bin/env python3
"""Read-only verification of publicly visible LinkWiki directory citations.

No external form submission, no Google SERP scraping, no GSC rank claim.
Any HTTP error or blocking is reported as inconclusive, not 'link removed'.
"""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = "https://linkwiki.info/"
SITES = {
    "DevElif": "https://develif.com/s/website-search-and-address-guides-by-linkwiki",
    "MeWebLink": "https://meweblink.com/website/linkwiki",
    "Ignlab Launch": "https://launch.ignlab.net/t/linkwiki-2",
    "OpenWebSide": "https://openwebside.com/products/757213b7-1ce9-41ed-9eb2-6bae9af82688",
    "OpenWebSide (older public listing)": "https://openwebside.com/products/757213b7-1ce9-41ed-b0d7-a807df42adf7",
    "SaaSKR": "https://saaskr.com/saas/linkwiki-info",
    "Sidedock": "https://sidedock.io/products/%EB%A7%81%ED%81%AC%EC%9C%84%ED%82%A4linkwiki",
    "Tistory address guide": "https://blacktetherscan.tistory.com/2",
    "StartupAccelerator": "https://startupaccelerator.dev/project/linkwiki",
    "PHIndex": "https://phindex.si/en/products/linkwiki.info",
    "VibeLabs Lab (self-authored listing)": "https://vibelabs.kr/lab/projects/238",
    "Cozit (self-authored listing)": "https://cozit.app/projects/716284cf-ad69-42af-970c-ad3874860797",
    "JocoHunt (self-authored listing)": "https://jocohunt.com/p/3k65c9py",
    "GitHub public project README (self-authored)": "https://github.com/a01088293068-ui/link",
}
REPORT = ROOT / "seo/backlink-public-check-report.md"


class LinkInspector(HTMLParser):
    def __init__(self, page_url):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.matches = []
        self.destinations = []
        self.robots = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(attrs.get("content", ""))
        if tag != "a" or not attrs.get("href"):
            return
        url = urlparse(urljoin(self.page_url, attrs["href"]))
        # The canonical listing landing is just as important as the homepage.
        # Do not treat linkwiki.info-looking subdomains, credentials, legacy
        # .html URLs, or offsite links as direct canonical referrals.
        if (url.scheme == "https" and url.hostname == "linkwiki.info"
                and not url.username and not url.password and
                url.port in (None, 443) and url.path in ("", "/", "/directory")):
            self.matches.append(attrs.get("rel", ""))
            self.destinations.append(url.path or "/")


def check_one(name, url, fetch=None):
    if fetch is None:
        def fetch(page):
            req = Request(page, headers={"User-Agent": "LinkWiki-CitationAudit/1.0"})
            with urlopen(req, timeout=18) as res:
                return res.getcode(), res.geturl(), res.read(700_000)
    try:
        status, final_url, body = fetch(url)
        if status != 200:
            return {"name": name, "url": url, "state": "unverified",
                    "detail": f"HTTP {status}"}
        parser = LinkInspector(final_url)
        parser.feed(body.decode("utf-8", errors="replace"))
        if not parser.matches:
            state, detail = "no_direct_link", "200 OK but no direct https://linkwiki.info/ anchor in fetched HTML"
        else:
            rels = [" ".join(r.split()) if isinstance(r, str) else " ".join(r)
                    for r in parser.matches]
            noindex = any("noindex" in meta.lower() for meta in parser.robots)
            state = "public_link_found"
            paths = sorted(set(parser.destinations))
            detail = (f"{len(rels)} direct href(s), targets={paths}, "
                      f"rel={rels}; meta_noindex={noindex}")
        return {"name": name, "url": url, "state": state, "detail": detail,
                "targets": sorted(set(parser.destinations))}
    except HTTPError as exc:
        return {"name": name, "url": url, "state": "unverified",
                "detail": f"HTTP {exc.code} (may be temporary or bot-blocked)"}
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {"name": name, "url": url, "state": "unverified",
                "detail": type(exc).__name__}


def distinct_referring_domains(rows):
    """Count domain diversity, never multiple pages on the same host as new domains."""
    return sorted({
        urlparse(row["url"]).hostname.removeprefix("www.")
        for row in rows
        if row["state"] == "public_link_found"
        and urlparse(row["url"]).hostname
    })


def markdown(rows):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# LinkWiki external public citation check — {now}", "",
             "Read-only HTTP checks. 200 + direct HTML anchor proves only current link visibility, not Google indexing or SEO value.",
             "403/404/errors are NOT treated as permanent deletion without separate human verification.",
             "Confirmed distinct referring domains in this HTTP sample: " +
             str(len(distinct_referring_domains(rows))) +
             " (pages on the same domain count once; self-authored listings are not independent endorsements).",
             "", "| Source | Result | Target pages | Evidence |", "|---|---|---|---|"]
    for r in rows:
        detail = r["detail"].replace("|", "/").replace("\n", " ")
        targets = ", ".join(r.get("targets") or []) or "미확인"
        lines.append(f'| [{r["name"]}]({r["url"]}) | {r["state"]} | '
                     f'{targets} | {detail} |')
    lines.extend(["", "Target: https://linkwiki.info/", "No submissions, credentials, or paid services were used.", ""])
    return "\n".join(lines)


def main():
    rows = [check_one(name, url) for name, url in SITES.items()]
    REPORT.write_text(markdown(rows), encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))
    # Link vanishing or a provider outage should not prevent future checks.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
