# LinkWiki /directory intent differentiation and live verification — 2026-11-09

## Observations
- Authenticated Search Console stored URL Inspection: `https://linkwiki.info/directory` was successfully crawled by smartphone Googlebot on 2026-11-08 but remains **Crawled — currently not indexed**. Self-canonical and Google-selected canonical agree. No confirmed duplicate-content classification.
- Actual live homepage `https://linkwiki.info/`: title `주소모음·링크모음·사이트모음 | 97개 사이트 검색 - 링크위키`, canonical homepage, index/follow.
- Actual live full directory `https://linkwiki.info/directory`: static HTML with all 97 original listing cards and distinct, multi-category searchable utility; distinct from homepage's shorter excerpts.
- Both pages were accessible from the public internet, and both still permitted indexing at the time of verification.

## Implemented changes
- Full directory metadata title changed from `주소모음·링크모음·사이트모음 검색 | 97개 사이트 - 링크위키` to **`사이트모음 전체 목록: 97개 사이트 검색 | 링크위키`**, reflecting its full-list/search intent.
- Full directory description now explicitly describes all 97 entries, domain search, categories, and non-ranking limitations; synchronized normal, Open Graph and Twitter titles/description.
- Homepage metadata and the current JavaScript-sensitive directory H1 remain unchanged.
- `seo/significant-page-updates.json` records genuine Nov 9 /directory metadata update for sitemap lastmod.
- Extended `build.py` Korean dynamic count handling to accept `97개 사이트를` as well as `97개 사이트의`, preserving validation if record count changes.
- Added regression tests for differentiated SEO titles, extensionless canonical, dynamic count substitutions, and existing preserved directory UI.

## Validation and notes
- Intermediate commit initially failed QA because the static site count rewriter relied on an overly narrow Korean grammar pattern. Fixed in `build.py`; **do not claim any earlier failing run passed**.
- Final independent GitHub Actions **passed**: https://github.com/a01088293068-ui/link/actions/runs/42569649836 .
- Independently fetched public `/directory` after deployment and verified the new title and description, `https://linkwiki.info/directory` canonical and `index,follow` robots.
- Independently fetched homepage after deployment and verified title, canonical `https://linkwiki.info/` and `index,follow` unchanged.
- The title adjustment is a modest relevance/clarity change, **not** evidence that Google has indexed /directory or improved `주소모음`, `링크모음`, or `사이트모음` rankings. Recheck Google URL Inspection after a future dated Googlebot crawl.

No new backlink placements, paid services, or indexing requests performed in this batch.
