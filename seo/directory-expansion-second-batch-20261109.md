# LinkWiki.info directory expansion — second quality-checked batch (2026-11-09)

## Goal

Increase the actual useful outbound website inventory of the SEO information site linkwiki.info without adding fake sites, duplicate domains, or unsupported safety/availability claims. This is **not** referring-domain backlink acquisition and makes no claim of higher Google ranking.

## Verified second batch (+18)

| Existing category | Added | Names |
|---|---:|---|
| AI 도구 | 5 | Google AI Studio, Gamma, ElevenLabs, QuillBot, Runway |
| 검색·포털 | 4 | 네이트, 줌, Startpage, Qwant |
| 스포츠 | 4 | UEFA, MLB, Formula 1, FotMob |
| 영상·OTT | 2 | Apple TV, Prime Video |
| 만화·웹툰 | 3 | WEBTOON (글로벌), Tapas, Tappytoon |
| **Total** | **18** | **118 → 136 listings** |

Each of the 18 responded with meaningful public page metadata/content during a read-only page retrieval. Eight other candidates were **excluded from this batch** because the retrieval returned timeouts or other access errors (Adobe Firefly, FIFA, Twitch, Dailymotion, Crunchyroll, 딴지일보, 82쿡, 기글하드웨어); this does not mean they are dead or unsafe. None of the new names or normalized destination hosts appeared in the prior 118-item source.

## Implemented, synchronized

- `assets/verified-directory.json`: 136 actual unique records.
- `assets/directory.js`: all 136 records used by actual full directory search.
- `directory.html`: 136 full static crawlable destination cards; correct title, description, visible count.
- `index.html`: homepage title, metadata, JSON-LD, primary lead copy and search count updated to 136.
- Five existing category pages (`ai`, `search`, `sports`, `video`, `webtoon`) contain their correct new category records.
- `build.py` homepage editorial compatibility adjusted for revised count.
- Original 118 entries unchanged; main LinkWiki service not touched; no new categories, no SEO doorway pages or generic-keyword-stuffed articles added.
- Existing Google-read sitemap-v2 config was **not changed**.

## Evidence

- Final GitHub QA: https://github.com/a01088293068-ui/link/actions/runs/42579638006 — **success**.
- During intermediate commits, the independent QA reported listing count mismatches and failed until source HTML, browser JS, category pages and tests were reconciled. Do not count intermediate failures as passed.
- Independent public read after release:
  - `https://linkwiki.info/` published title shows 136.
  - `https://linkwiki.info/directory` eventually showed the new 136 title, count, and 169 extracted links; earlier fetch had shown the old title due to propagation or cache, but the subsequent fetch confirmed a fresh version.
  - `https://linkwiki.info/categories/ai` includes Gamma.
  - `https://linkwiki.info/categories/search` includes Qwant.
- Google has NOT yet confirmed a new indexation or ranking change after this expansion. Exact target keyword rank progress remains unverified.

## Measurement caveats

This expansion is user-value work; its count increase alone is not a search ranking factor. Indexation of the full /directory after the previous Nov 8 stored Google crawl is not newly confirmed. GSC comparative query measurements must use a later identical time window.
