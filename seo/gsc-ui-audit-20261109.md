# LinkWiki — direct Google Search Console UI audit (2026-11-09)

Property: `sc-domain:linkwiki.info` (authenticated property owner view).
Evidence:
- Manual Actions, Security Issues, Pages overview: https://agent.tinyfish.ai/runs/c5b093db-2bea-4e7c-95ef-7a2310cda2a6
- Sitemaps & search queries: https://agent.tinyfish.ai/runs/0ac6dff4-3ff0-415c-89ca-4f8fadebdce3

## Verified current UI report statuses

| Report | Observed status | Scope/limitations |
|---|---|---|
| Manual Actions | **No issues detected** | GSC property status on 2026-11-09; no manual action reported |
| Security Issues | **No issues detected** | Does not certify every external directory link |
| Page indexing overview | 10 indexed, 9 not indexed shown | Report showed last-updated **2026-10-22**, not a live total; GSC UI agent also reported 'all known 10', internally inconsistent with 10+9: do not interpret as exhaustive current counts |
| Non-indexed category | 9 'Page with redirect' | GSC chart dated 2026-10-22; zero/no entries for other reasons in this overview. Separately URL Inspection API on newer dates showed crawled-not-indexed for /directory; that newer per-URL state takes precedence for the URL |
| sitemap.xml | Submitted 2026-11-07, **Couldn't fetch**, never read in this GSC UI report | Does NOT mean live sitemap.xml currently returns an HTTP error. Independent HTTP fetch returns an XML sitemap of 28 URLs |
| sitemap-v2.xml | Submitted 2026-10-24, **Success**, last read 2026-10-24, 20 discovered URLs | Google has processed the fallback sitemap before; current live v2 has same 28 URLs as main sitemap (new content added since last Google read) |

## Latest target query performance shown in GSC UI

Performance report displayed approx. 2026-10-14 through 2026-11-07:
- 85 impressions, 30 clicks total; avg position 15.3 sitewide across all queries (not rank for generic target terms).
- `주소모음`: 1 impression, 1 click, average position 111.
- `링크모음`: 4 impressions, 1 click, average position 123.
- `사이트모음`: not present in exposed top queries; no rank claim possible.
- `링크위키`: 48 impressions, 20 clicks, average position 3.6.
- `주소 위키`: 9 impressions, 1 click, avg position 10.4.
- `주소위키`: 4 impressions, 0 clicks, avg position 19.8.

Earlier GitHub GSC API artifact ending Nov 6 recorded 73 impressions, 27 clicks over a different rolling window. Changes in totals must not be ascribed to same-day code changes; date ranges and processing lag differ.

## Site sitemap / robots verification

- Both `https://linkwiki.info/sitemap.xml` and `https://linkwiki.info/sitemap-v2.xml` independently fetched as **28-URL XML sitemaps** on 2026-11-09.
- Both are generated from the same canonical output file by `build.py`; Google already succeeded with v2 on an older, smaller sitemap.
- `robots.txt` now advertises **both** sitemap URLs without removing the original; Google supports multiple sitemap directives.
- `seo/search_console_monitor.py` updated to report both GSC sitemap processing histories, not mistakenly equate primary-fetch error with no sitemap read ever.
- Change is a discovery hint, **not** a confirmed Google recrawl or index action.

## Conclusions and next investigation

1. No evidence of a Google manual action or reported security issue.
2. Primary GSC sitemap fetch error is genuine in the UI, but live URL is accessible; inspect Cloudflare/edge request logs or Google crawl stats for transient host or Googlebot-specific errors before claiming a site error was fixed.
3. Existing Google-read v2 sitemap provides a source of URL discovery. Robots now includes it as well as the main sitemap.
4. GSC Page indexing overview is stale (2026-10-22) and should not override fresh URL-specific inspection results. 'Page with redirect' should be examined for legacy .html variants; do not remove valid canonical redirects without evidence.
5. SEO rankings for three generic search terms remain weak, and no page text edits or backlink counts should be claimed to have changed their rankings until a fresh comparable GSC interval is available.

No indexing requests, site verification changes, security modifications, credentials, or payment were performed.
