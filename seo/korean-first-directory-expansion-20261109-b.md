# LinkWiki.info Korean-first listings and practical navigation — 2026-11-09

## Outcome
171 → **183 distinct registered outbound site entries**, with twelve Korean services verified by direct public-page fetch. This changes `linkwiki.info` static informational directory only; no modifications to the distinct main LinkWiki app, admin, database or successfully processed sitemap-v2.xml. These are outbound links, not new backlinks to LinkWiki.

## Twelve new domestic site records

| Category | Names |
|---|---|
| 검색·포털 / 공공정보 | 정부24, 국세청 홈택스, 고용24, 기상청 날씨누리, 대한민국 정책브리핑, KOTRA 무역투자24 |
| 스포츠 | KBO 공식 홈페이지 (koreabaseball.com) |
| 영상·OTT (broadcast and streaming) | 멜론, FLO, EBS, SBS, MBC |

The existing category taxonomy is retained. 음악 스트리밍 멜론/FLO are listed in 영상·OTT as streaming/media services under the existing eight-category system; consider a dedicated 음악 category only if a wider editorial reorganization becomes justified.

All twelve direct URLs returned independently retrieved public page titles and some page content, but *not* a guarantee of ongoing uptime, safety or official status. 홈택스 returns minimal public extract but a title identifying the tax service. URLs with unclear or failed responses were held back. `tv.kakao.com` was explicitly excluded because its public page said '서비스 종료'.

## Implementation
- Source `assets/verified-directory.json` holds 183 records with unique hosts / names and retains all 171 earlier entries.
- `assets/directory.js` contains identical 183 records for browser search and category filtering.
- `directory.html` contains 183 original static indexable cards, real domain names, and accurate 183 title and visible counter.
- `categories/search.html` now has 28 records, `categories/sports.html` 17, and `categories/video.html` 18.
- `index.html` and `build.py` accurately present 183 everywhere including metadata.
- The existing `KOREAN_FIRST_SEARCH_NAMES` promoted four newly registered real Korean public information sites (정부24, 고용24, 기상청 날씨누리, 국가통계포털 KOSIS). Homepage and core listing have twelve Korean one-click search shortcuts, derived from actual records. They are not claimed to represent popularity or ranking.
- Registered names, descriptions and real destinations are shown as static HTML to crawlers. No new fake keyword doorway pages or safety badges.

## Verification
- Latest final GitHub build and all code regression checks: **success**, https://github.com/a01088293068-ui/link/actions/runs/42582876026
- Latest matching-revision live crawlability test: **success**, https://github.com/a01088293068-ui/link/actions/runs/42582903738
- Independent external public page fetch confirmed both `https://linkwiki.info/` and `https://linkwiki.info/directory` titles **183**, and twelve `/directory?q=` shortcut links on homepage.
- Individual public category views confirmed government services in search, KBO in sports, and EBS in video categories.

## Limits and next priorities
- This improves use of Korean-language directory pages and practical public service discovery. No evidence yet it improves exact search positions for 주소모음, 링크모음, 사이트모음 or changes stored Google /directory index status.
- Avoid bulk additions with no relevant category; new categories for books/musical streaming may be useful in a deliberate, separately tested taxonomy extension.
- Do not resubmit already successfully processed sitemap-v2 or invent backlink results.
