# LinkWiki generic-keyword ranking bottleneck — 2026-11-09

## Objective and verified status

The actual goal is top positions for **주소모음, 링크모음, 사이트모음**, NOT the brand query.

Latest completed Search Console API evidence:
https://github.com/a01088293068-ui/link/actions/runs/42574818928

Period: 2026-10-10–2026-11-06 (GSC API processing lag; newer 11/7 UI view exists).
- 주소모음: 1 impression; 111.0 average position; landing URL /.
- 링크모음: 4 impressions; 123.0 average position; landing URL /.
- 사이트모음: no disclosed query row; *not* evidence of zero searches.
- Homepage /: Google URL inspection PASS, crawl Oct 29.
- /directory: Google crawl Nov 8 successful, robots allowed, index allowed, Google selected canonical equals declared canonical; *not indexed* in stored inspection.
- URL Inspection API checked 20 URLs: 1 PASS, 11 unknown, 8 crawled/not indexed. This count cannot be treated as a verified total of all indexed pages because Search Analytics shows additional non-homepage pages with impressions, including /guides/address-check.
- Domain registered 2026-10-15; the website has ~25 days of current domain registration as of this review. Historical references to unrelated older uses of the same spelling do not establish a current manual action.
- Manual Actions and Security Issues reports previously checked in the authenticated GSC UI: no issues detected.
- sitemap-v2 already processed successfully by Google and was not changed.

## Why time-to-top cannot be guaranteed

Google explicitly states there is no guarantee or predictable date for crawl/index:
https://developers.google.com/search/help/crawling-index-faq
Google on indexing for new domains and crawled/not-indexed:
https://support.google.com/webmasters/answer/7440203?hl=en

The observations do not support attributing lack of indexation to robots, canonical, sitemap, or a manual penalty; Google may decline to index a crawled URL. Keyword rankings are very weak; a sequence of small HTML edits is not proven to change them.

## Highest impact work, priority order

1. Establish whether /directory is indexed after a new Googlebot crawl **later than 2026-11-09**, using a dated Search Console URL Inspection reading. Do not repeatedly submit an unchanged sitemap.
2. Preserve stable homepage title and canonical as the actual currently ranking URL for both exact generic keywords. Repeated title swaps are not measurable evidence of SEO improvement.
3. Grow real user value and differentiated site-specific data: verified provenance of original service descriptions, clear directory filters by task/domain, accurate listing maintenance disclosures. No fabricated freshness, popular rankings, safety endorsements, or duplicate keyword-heavy doorway pages.
4. Secure relevant independently editorial citations to the useful category/full-directory pages, not just one-off mass catalog profiles, and verify public hyperlinks. Distinguish self-authored, nofollow, and natural independent domains.
5. Compare the exact three queries over two **matching seven-day GSC date windows**, alongside query-page observations and a dated recrawl status. Require more than one impression before making strong rank-change claims.
6. Reduce gratuitous main-branch content churn: let Google process substantive edits before changing the same landing page again. Keep automated build and performance checks running.

## New instrumentation validated this batch

`seo/search_console_monitor.py` reports conflicts where Google Search Analytics has actual search impressions for URLs that still show non-PASS stored URL Inspection results. This prevents treating a lagging inspection count as proof that all other pages never appear in search.

Code and tests: commits cab113081fdf6488f60abbd3e3fd0364ad5b9d1b to fa9b941b32543a972068d43e61bd319cb11d92fe.
Final passed QA: https://github.com/a01088293068-ui/link/actions/runs/42575601861 .

This is improved diagnostic accuracy, not proven rank improvement. No external submission or payment was made.
