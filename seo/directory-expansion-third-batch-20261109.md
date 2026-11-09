# LinkWiki.info — third directory expansion (2026-11-09)

## Verified public destinations added (18, 136 → 154)

| Category | Count | Names |
|---|---:|---|
| AI 도구 | 3 | Ideogram, Suno, Leonardo AI |
| 검색·포털 | 4 | Mojeek, Swisscows, Yandex, WolframAlpha |
| 스포츠 | 5 | NFL, NHL, ATP Tour, WTA Tennis, BBC Sport |
| 영상·OTT | 4 | Plex, Rakuten Viki, MUBI, Pluto TV |
| 만화·웹툰 | 1 | INKR Comics |
| 커뮤니티 | 1 | Hacker News |
| **Total** | **18** | **154** |

24 candidate sites were fetched via read-only public page-content retrieval: 18 had meaningful public titles and text and were not already represented by destination host or listed name. Six candidates were held back because retrieval could not establish content: Mistral Le Chat, Character.AI, MANGA Plus, Stack Overflow, Product Hunt, Quora. These are not declared unavailable or unsafe.

## Full synchronization

- `assets/verified-directory.json`: 154 records, existing 136 unchanged.
- `assets/directory.js`: 154 records for browser-based name/domain/category search.
- `directory.html`: 154 original static listing cards, count and metadata.
- Six category pages (`ai`, `search`, `sports`, `video`, `webtoon`, `community`) updated with real new listings and correct counts.
- `index.html` source metadata/title/JSON-LD/visible explanatory count updated to 154; `build.py` compatibility editorial copy updated to 154.
- Legacy full directory app not connected or touched, and the previously successful sitemap-v2 configuration was not changed.

## Verification

- Final independently executed build and full regression tests: **passed**, https://github.com/a01088293068-ui/link/actions/runs/42581611064 .
- Independent live directory HTML extractor retrieved `https://linkwiki.info/directory` showing **154** and 187 extracted links.
- Live category pages contained new entries: Ideogram, Swisscows, NFL and Hacker News in their correct categories.
- Live homepage initially showed **154 in the body** but an older **136** title during propagation; subsequently re-fetched the public homepage and confirmed title and body both **154**, along with public /directory title and body both **154**. Do not mistake intermediate propagation state for the final release.
- Public crawlability smoke workflow run: https://github.com/a01088293068-ui/link/actions/runs/42581638518 (status was in progress when this note was drafted; check final conclusion before claiming success).

## Search interpretation

These are useful outbound site listings, **not backlinks to linkwiki.info**. No evidence yet for changed Google indexing or improved exact query rankings for 주소모음, 링크모음, 사이트모음. Avoid repeatedly changing successful sitemap-v2 or inventing ranks.
