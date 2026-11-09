# LinkWiki 97 external listing destinations — live verification and false-positive review

Date: 2026-11-09 UTC.

## Why this matters
LinkWiki's core generic-query offering is the ability to search and follow real external site links. Broken destinations reduce user value. This verification is a **user utility/quality investigation**, NOT evidence of improved Google ranking or a claim that every third-party destination is safe.

## Source of truth and evidence

- 97 existing records from `assets/verified-directory.json`; none added, removed, re-ranked or automatically replaced.
- First independent GitHub Actions run: https://github.com/a01088293068-ui/link/actions/runs/42576603891
  - 67 HEAD 2xx/reachable, 3 HEAD 404, 3 redirect, 20 restrictions, 2 network errors, 2 other results.
- **False positives found:** independent page GET rendered real, current content for `https://www.francezone.com/` and `https://www.topdigital.com.au/`, even though their HEAD requests returned 404. The `https://www.daum.net/` page GET timed out in the separate browser extraction, so a HEAD 404 never justified declaring Daum dead.
- Fixed `seo/external_link_health.py` to attempt safe header-only GET for HEAD statuses 404/405/410/501 before classifying. It never follows redirects to unreviewed destinations, downloads bodies, authenticates, posts, collects passwords, or deletes listings. Added 2 regression cases proving false-404 handling.
- Recheck after code change: https://github.com/a01088293068-ui/link/actions/runs/42576814847 — **success**
  - **75 reachable**, **0 broken candidates**, 3 redirects, 15 restricted/unknown, 2 network-unconfirmed, 2 other. The increase from 67 to 75 is attributable to better HTTP checking, **not** site operator repairs or eight newly fixed destinations.

## Secondary separate page GET examination of the 22 inconclusive URLs
Five successfully yielded actual visible content through a browser-compatible fetch:
- `https://bemypet.kr/` (비마이펫)
- `https://ohou.se/` (오늘의집)
- `https://www.espn.com/` (ESPN)
- `https://www.netflix.com/kr/` (넷플릭스)
- `https://ridibooks.com/` (리디)

The remaining **17 are inconclusive** under this separate extraction due to bot blocking, timeouts or target unreachable responses; not proof they are closed or invalid. The original 22 not fully proven by HEAD+GET include 3 redirect cases; redirects are not counted as dead sites.

Special review candidates:
- `https://turkeykorean.net/home/index.php`: network error in CI, target_unreachable during browser fetch, but third-party listings still mention `turkeykorean.net` as an association site. **No replacement URL verified**. Do not silently redirect users to a different group.
- `https://www.korea.com.sg/`: timeout in both tools, not known dead.
- `https://www.fmkorea.com/`: HTTP 430 likely access restriction; no current availability guarantee.
- Major providers that block automated requests (e.g. Claude, Perplexity, Naver Webtoon) cannot be labelled dead on that basis.

## Safety, maintenance and next decision
- The workflow runs weekly (Monday) or manually, keeping a 30-day downloadable report artifact; no automatic edits.
- Do not publish badges saying *verified working* based on these results; it only checked responses at one moment.
- Avoid making mass updates to sitemap or re-requesting URL indexing; `sitemap-v2.xml` was already successfully processed in GSC.
- Google Search Console continues to show `/directory` crawled-but-not-indexed as of Nov 8 stored inspection. Nothing here proves this investigation changed that or the positions of `주소모음`, `링크모음`, `사이트모음`.
- Mark a site as broken only after an independent normal browser check with durable evidence and, if replacing it, a confirmed official replacement.
