# LinkWiki keyword-first directory improvement — November 9, 2026

## Goal
Improve actual utility of the indexable `/directory` page and make `주소모음`, `링크모음`, `사이트모음` search intent useful for visitors. No work on the already-successfully-processed sitemap-v2.xml.

## Data-backed findings
- Google URL Inspection last stored state: `https://linkwiki.info/directory` crawled on Nov 8, but **currently not indexed**, with no blocking robots/noindex or canonical conflict identified at that inspection.
- Three head terms are weak: `주소모음` 1 impression/111 avg rank; `링크모음` 4 impressions/123 avg rank; `사이트모음` no disclosed query row, which is not proof of zero searches.
- A newer, exact-and-related-family GSC API report from run https://github.com/a01088293068-ui/link/actions/runs/42572049092 completed successfully. Distinct reporting prevents a 6th-place `주소모음 위키` result from being mistaken for `주소모음` performance.
- Most visits still originate on homepage; core directory was not exposed as an observed search landing page.

## Implemented in this batch
- The existing `/directory` text helps users understand site name/domain search but previously had no direct examples of *functional search links*.
- Updated `build.py::directory_search_help` to construct 3 exact, executable `/directory?q=<URL-encoded registered name>` search links using real verified directory entries in three distinct topics (search, AI and sports).
- Example names are selected from the actual `assets/verified-directory.json`. They are not "popular", "verified safe", newly available or ranked; text explicitly disclaims those claims.
- The site's existing `assets/directory.js` already handles `q` via URLSearchParams and fills search results; no script rewrite required.
- Added regression test to assert three real site names are linked and `/directory?q=` URLs decode to existing registered names. Test also checks the section exists once in generated HTML.
- No change to homepage, category counts, sitemap-v2, canonical, site directory data, or LinkWiki main-service connection.

## Evidence and outcome
- Source code commit: https://github.com/a01088293068-ui/link/commit/49c0007b84f9401df08490dbac70ca1255664f25
- Test commit: https://github.com/a01088293068-ui/link/commit/34eddb8a6d3dc348c791911e500fbe8142c422ff
- Build QA: https://github.com/a01088293068-ui/link/actions/runs/42572963291 — **successful**.
- Public deployment HTTP extraction exposed three working deep links:
  - `https://linkwiki.info/directory?q=%EB%84%A4%EC%9D%B4%EB%B2%84`
  - `https://linkwiki.info/directory?q=ChatGPT`
  - `https://linkwiki.info/directory?q=%EB%84%A4%EC%9D%B4%EB%B2%84%20%EC%8A%A4%ED%8F%AC%EC%B8%A0`
  All are produced from existing registered names. Static content extraction can discard headings inside the dynamically enhanced page; links were independently extracted.
- Independent public crawlability workflow also passed on this revision: https://github.com/a01088293068-ui/link/actions/runs/42572968322

## Limitations / follow-through
- Link usability and CI success are confirmed, **not** improvement in Google ranking, crawl selection, or indexation.
- Do not over-interpret `/directory` search query params as distinct indexable pages: their canonical remains the same `/directory` page.
- Wait for Google crawl after Nov 9 before comparing index/rank effects; compare like-for-like GSC query reporting windows.
