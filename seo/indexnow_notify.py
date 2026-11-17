#!/usr/bin/env python3
"""Notify Naver IndexNow only about LinkWiki pages changed in this commit.

IndexNow accelerates discovery; it does not guarantee crawling, indexing, or
ranking. URLs are derived from changed source files and intersected with the
current canonical sitemap to avoid sending stale or non-canonical paths.
"""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SITE = "https://linkwiki.info"
HOST = "linkwiki.info"
KEY = "53f284d85bb5eed6bab927f5a93d8da8"
KEY_URL = SITE + "/" + KEY + ".txt"
ENDPOINT = "https://searchadvisor.naver.com/indexnow"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
CATALOG_FILES = {
    "assets/verified-directory.json",
    "assets/directory-evidence.json",
}


def sitemap_urls(xml_bytes):
    root = ET.fromstring(xml_bytes)
    if root.tag != NS + "urlset":
        raise ValueError("current sitemap is not a standard urlset")
    urls = []
    for node in root.findall(NS + "url/" + NS + "loc"):
        value = (node.text or "").strip()
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or parsed.netloc != HOST
                or parsed.query or parsed.fragment or not parsed.path.startswith("/")):
            raise ValueError("non-site or malformed URL in sitemap: " + value)
        path = parsed.path
        # The tracked source sitemap may contain physical .html filenames;
        # the release builder publishes their clean extensionless canonicals.
        if path.endswith("/index.html"):
            path = path[:-len("index.html")]
        elif path.endswith(".html"):
            path = path[:-5]
        value = urlunsplit(("https", HOST, path, "", ""))
        urls.append(value)
    if len(urls) != len(set(urls)):
        raise ValueError("duplicate URL in sitemap")
    return set(urls)


def public_path_for_source(path):
    """Map a changed published HTML/Markdown source to its clean public URL."""
    path = path.replace("\\", "/").lstrip("./")
    if path == "index.html":
        return SITE + "/"
    if path == "directory.html":
        return SITE + "/directory"
    if path == "categories/index.html":
        return SITE + "/categories/"
    if path.startswith("categories/") and path.endswith(".html"):
        slug = path.rsplit("/", 1)[1][:-5]
        return SITE + "/categories/" + slug
    if path == "guides/index.html":
        return SITE + "/guides/"
    if path.startswith("guides/") and path.endswith(".html"):
        slug = path.rsplit("/", 1)[1][:-5]
        return SITE + "/guides/" + slug
    if path.startswith("content/") and path.endswith(".md"):
        slug = path.rsplit("/", 1)[1][:-3]
        if slug:
            return SITE + "/blog/" + slug + "/"
    return None


def changed_page_urls(changed_paths, available_urls):
    """Return only sitemap-backed pages materially affected by changed sources."""
    paths = {str(path).replace("\\", "/").lstrip("./") for path in changed_paths}
    urls = set()
    if "build.py" in paths:
        return sorted(set(available_urls))
    if paths & CATALOG_FILES:
        urls.update(url for url in available_urls if (
            url == SITE + "/" or url == SITE + "/directory"
            or url == SITE + "/categories/" or url.startswith(SITE + "/categories/")
        ))
    for path in paths:
        url = public_path_for_source(path)
        if url and url in available_urls:
            urls.add(url)
        if path.startswith("content/") and path.endswith(".md"):
            if SITE + "/blog/" in available_urls:
                urls.add(SITE + "/blog/")
            if SITE + "/" in available_urls:
                urls.add(SITE + "/")
    return sorted(urls)


def changed_files(base, head):
    if not base or set(base) == {"0"}:
        command = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", head]
    else:
        command = ["git", "diff", "--name-only", base, head]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def verify_key(fetch=urlopen):
    request = Request(KEY_URL, headers={"User-Agent": "LinkWiki-IndexNow/1.0"})
    with fetch(request, timeout=15) as response:
        if response.status != 200 or response.read(256).decode("utf-8").strip() != KEY:
            raise RuntimeError("public IndexNow ownership key could not be verified")


def submit(urls, fetch=urlopen):
    if not urls:
        return 0
    payload = json.dumps({
        "host": HOST,
        "key": KEY,
        "urlList": urls,
    }, ensure_ascii=False).encode("utf-8")
    request = Request(
        ENDPOINT,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "LinkWiki-IndexNow/1.0"},
    )
    try:
        with fetch(request, timeout=35) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
    if status not in (200, 202):
        raise RuntimeError("Naver IndexNow rejected the update (HTTP " + str(status) + ")")
    return status


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    paths = changed_files(args.base, args.head)
    with open("sitemap.xml", "rb") as source:
        available = sitemap_urls(source.read())
    urls = changed_page_urls(paths, available)
    if not urls:
        print("INDEXNOW: no changed canonical pages to notify")
        return 0
    verify_key()
    status = submit(urls)
    print("INDEXNOW: Naver accepted " + str(len(urls)) + " changed URL(s), HTTP " + str(status))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Do not print request bodies, authentication material, or raw responses.
        print("INDEXNOW_ERROR: " + type(error).__name__ + ": " + str(error), file=sys.stderr)
        raise SystemExit(1)
