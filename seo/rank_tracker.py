#!/usr/bin/env python3
"""Observe LinkWiki appearances in the first page of a fixed Korean SERP sample.

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
KEYWORDS = ("링크모음", "주소모음", "사이트모음",
            "링크모음 사이트", "주소모음 사이트", "사이트모음 추천")
API_URL = "https://google.serper.dev/search"


def search(query, key):
    body = json.dumps({"q": query, "gl": "kr", "hl": "ko", "num": 10}).encode()
    request = Request(API_URL, body, {
        "X-API-KEY": key, "Content-Type": "application/json",
        "Accept": "application/json", "User-Agent": "LinkWiki-RankMonitor/1.0",
    }, method="POST")
    with urlopen(request, timeout=25) as response:
        return json.load(response).get("organic", [])


def find_result(results, domain=TARGET):
    for index, result in enumerate(results, 1):
        url = str(result.get("link") or "")
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        if host == domain or host.endswith("." + domain):
            return {"position": index, "url": url}
    return {"position": None, "url": None}


def collect(fetch, queries=KEYWORDS):
    observations = {}
    for query in queries:
        observations[query] = find_result(fetch(query))
    return observations


def main():
    key = os.environ.get("SERPER_API_KEY", "").strip()
    if not key:
        raise SystemExit("SERPER_API_KEY is missing")
    observations = collect(lambda q: search(q, key))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if HISTORY.exists():
        history = json.loads(HISTORY.read_text(encoding="utf-8"))
    else:
        history = {"schema": 1, "measurement": "Serper top 10, gl=kr, hl=ko", "samples": []}
    day = now[:10]
    history["samples"] = [x for x in history["samples"] if x["date"] != day]
    history["samples"].append({"date": day, "observed_at": now, "results": observations})
    history["samples"] = sorted(history["samples"], key=lambda x: x["date"])[-90:]
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for keyword, result in observations.items():
        pos = result["position"]
        print(f"{keyword}: {pos if pos is not None else 'outside observed top 10'}")
    print("Positions are one non-personalized API sample, not universal Google rankings.")


if __name__ == "__main__":
    main()
