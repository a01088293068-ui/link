# LinkWiki /directory repeated-copy reduction — 2026-11-09

## Context
- Core search intent remains 주소모음 / 링크모음 / 사이트모음; latest GSC data still shows no measured improvement attributable to today's changes.
- Google stored inspection for https://linkwiki.info/directory last crawled Nov 8 and reported **Crawled — currently not indexed**. The Nov 9 changes have no confirmed post-edit Google crawl.
- The sitemap-v2.xml processing success is established and was **not revisited**.

## Change made
- Previously, each of the 97 full list cards had a distinct explanatory description, but `build.py::directory_category_overview` then repeated the same descriptions for up to three examples in each category, creating avoidable duplicate paragraphs on one page.
- The secondary category comparison now contains real registered service names and actual parsed hostnames, counts, unique category purpose guidance and links to the full category listing, **but does not reprint the listing descriptions**.
- The 97 full HTML cards, their descriptions and outbound URLs remain unchanged, as do the homepage, category navigation, search JS and canonical settings.
- Disclaimers remain: listing presence does not verify safety, official operation, pricing or current availability.

## Regression checks
- Updated tests assert genuine registered names and domains, correctly escaped HTML, and no duplicated sample description in the overview.
- An intermediate QA run failed because the old regression assertion expected duplicated explanatory copy; it was corrected alongside the new behavior. This is not represented as a passing run.
- Final build QA **passed**: https://github.com/a01088293068-ui/link/actions/runs/42574754352 .
- Public crawlability workflow **passed** for the same commit: https://github.com/a01088293068-ui/link/actions/runs/42574785595 .
- A separate text extractor did not reliably include the editorial section in its rendered extraction; therefore only the CI's successfully matched release checks support production consistency. Do not claim separately confirmed editorial string from that extractor.

## Important limits
- This improves redundant page copy and human scanability; it does **not prove** a Google ranking or indexation change.
- The remaining primary bottleneck is Google's non-indexed stored assessment of `/directory`. Re-check after a later Google crawl rather than requesting repeated indexing of an unchanged page.
