# LinkWiki.info — Korean-first information-site update (2026-11-09)

## Decision
The intended audience searches in Korean for 주소모음, 링크모음, 사이트모음. Recent expansion leaned too heavily toward global services. New registrations now prioritize **real Korean-operated / Korean-focused services and public information**, without deleting previously published foreign entries or changing the separate core LinkWiki directory app.

## Domestic additions: 17 records

| Existing category | Count added | Korean-oriented examples |
|---|---:|---|
| AI 도구 | 5 | 뤼튼, 클로바노트, 타입캐스트, 브루(Vrew), 미리캔버스 |
| 검색·포털 | 6 | 카카오맵, 국가법령정보센터, 공공데이터포털, 국가통계포털 KOSIS, 국립중앙도서관, 한국민족문화대백과 |
| 스포츠 | 2 | 대한축구협회, KLPGA |
| 영상·OTT | 1 | 치지직 |
| 만화·웹툰 | 1 | 탑툰 |
| 만화·웹소설 | 2 | 조아라, 노벨피아 |
| **Total** | **17** | **154 → 171 published records** |

32 Korean-oriented candidates were initially considered. Direct independent retrieval returned pages for the 17 registered entries, and a separate public web search independently established that 치지직 is a current real streaming site. Other choices were excluded pending confirmation, including the page `https://tv.kakao.com/`, which returned an explicit **서비스 종료** title; it should not be promoted as currently active. A timeout/403 on other candidates is inconclusive, not evidence of failure or closure.

## Implementation

- `assets/verified-directory.json`: 171 records, existing 154 unchanged.
- `assets/directory.js`: 171 searchable records.
- `directory.html`: 171 static crawlable listing cards with accurate metadata.
- `index.html`: updated 171 in title, descriptions, structured data, visible search copy.
- Six category pages updated: `ai` 22, `search` 22, `sports` 16, `video` 13, `webtoon` 13, `comics-directory` 7.
- `build.py`: compatible editorial source count, and a **prominent Korean-first shortcut section** with eight registered Korean-oriented services on the homepage and above the full-directory search box.
- No invented popularity ordering. Korean-first navigation is curated and represents site *topics*, not a ranking, recommendation, affiliation or guarantee of safety.
- Existing sitemap-v2 configuration was not changed.

## Verification

- Final independent GitHub release QA and regression suite **success**: https://github.com/a01088293068-ui/link/actions/runs/42582500296 .
- Independent public release crawlability smoke **success**: https://github.com/a01088293068-ui/link/actions/runs/42582526999 .
- Public `https://linkwiki.info/` and `https://linkwiki.info/directory` both returned titles including **171**.
- Public category pages showed 뤼튼, 카카오맵, 대한축구협회, 치지직 and 조아라 in their expected category.
- Independent public HTML link extraction found eight Korean search deep links in homepage and eight in directory; no duplicated shortcut blocks.
- No new GSC index or ranking improvement attributable to these changes has been verified, and the already-successful sitemap-v2 was not modified.

## Next content policy
New additions should be predominantly domestic/Korean-language resources. Validate the site and operating status before publishing, focus on utility and relevance rather than sheer count, preserve editorial caution regarding safety, and keep full-list/card/JS/category data synchronized.
