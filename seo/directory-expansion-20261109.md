# LinkWiki.info — 97 → 118 verified directory entries (2026-11-09)

## Purpose and boundary

Add user-useful destinations to the static SEO information site `https://linkwiki.info`. This is **not** a backlink-building operation; these are outbound listings, not referring domains. The separate main LinkWiki service and database were **not** changed. Adding listings does not itself guarantee Google indexing or target keyword ranking improvements.

## Added 21 genuine entries (six existing categories)

| Category | Count added | Entries |
|---|---:|---|
| AI 도구 | 5 | Microsoft Copilot, NotebookLM, DeepL, Canva, Hugging Face |
| 검색·포털 | 4 | DuckDuckGo, Brave Search, Ecosia, Yahoo |
| 스포츠 | 1 | K리그 |
| 영상·OTT | 2 | 디즈니+, Vimeo |
| 만화·웹툰 | 4 | 레진코믹스, 투믹스, 네이버 시리즈, 봄툰 |
| 커뮤니티 | 5 | 뽐뿌, 아카라이브, 레딧, 브런치스토리, 네이버 지식iN |
| **Total** | **21** | **97 → 118 records** |

All 21 were previously absent by normalized destination host and existing name. Before publishing, fetched each of 28 candidate public pages through an independent web-content service; these 21 returned actual page metadata and content. Seven candidates were held back (Poe, KBO, NBA, Olympics, Coupang Play, Watcha, Ruliweb) after login-required, timeout, bot block or invalid URL responses. These outcomes do not prove the seven services are unsafe or down, only that this verification path could not adequately confirm them.

## Implemented

- `assets/verified-directory.json`: +21 name, category, URL and concise truthful description objects.
- `assets/directory.js`: mirrored all 118 actual records for working browser search and filters.
- `directory.html`: 118 crawlable HTML service cards, accurate title, OpenGraph/Twitter descriptions and visible count.
- Six actual category HTML pages: `ai` (4→9), `search` (4→8), `sports` (4→5), `community` (26→31), `video` (4→6), `webtoon` (4→8).
- `index.html`: home title, description, JSON-LD description, page heading, visible search guidance and OpenGraph metadata changed consistently from 97 to 118.
- `build.py`: existing homepage intent function recognized new published count.
- Existing release and AI-content tests now read published real records instead of falsely assuming 97 entries, while preserving fixed toy input test cases.

The original 97 records, their descriptions and outbound URLs were kept unchanged. No invented contact data, live uptime, Google rank, latest verification dates, safety endorsements or fake rankings were added.

## Verified

- Successful final GitHub SEO build and regression suite:
  https://github.com/a01088293068-ui/link/actions/runs/42578857741
- Successful independent live crawlability parity:
  https://github.com/a01088293068-ui/link/actions/runs/42578889305
- Independent public fetch confirmed updated `https://linkwiki.info/directory` title shows 118, `/categories/ai` includes Microsoft Copilot and NotebookLM, and `/categories/search` includes DuckDuckGo.
- Intermediate QA failures existed when JSON, JS, HTML and category pages were not yet synchronized and old tests assumed exactly 97 entries; all repaired before final success. Do not count those intermediate attempts as successful deployment.

## Search performance impact

No fresh Google crawl, index verdict or GSC ranking change has been measured after these 21 new records. Main targets remain 주소모음, 링크모음, 사이트모음; improving navigable inventory is a user-facing content enhancement, **not** proof of top rankings. The successfully processed sitemap-v2 configuration was not altered.
