# LinkWiki keyword-first priority report — November 9, 2026

## Objective
Rank improvements for **주소모음 / 링크모음 / 사이트모음**. Brand '링크위키' rankings are secondary. Do not conflate related queries with the three exact head terms.

## Observed Google Search Console data
Authenticated property: `sc-domain:linkwiki.info`.
Browser evidence: https://agent.tinyfish.ai/runs/5b164b7e-99cb-47b6-a470-8deb6f79b2fe
Latest exposed performance date: **November 7, 2026**. The report's date control covered October 14 – November 7.

| Exact query | Impressions | Clicks | Mean position | Observed landing |
|---|---:|---:|---:|---|
| 주소모음 | 1 | 1 | 111.0 | Homepage is the dominant observed landing for core search; exact query×URL pair not newly verified in this UI run |
| 링크모음 | 4 | 1 | 123.0 | Homepage is the dominant observed landing; exact query×URL pair not newly verified in this UI run |
| 사이트모음 | No disclosed query row | — | — | No query×URL row available |

Related queries **must not inflate the head-term rank**:
- `주소 위키`: 9 impressions, 1 click, avg position 10.4.
- `주소위키`: 4 impressions, 0 clicks, avg position 19.8.
- `주소모음 위키`: 1 impression, 1 click, avg position 6.0.
- `주소모아 위키`: 2 impressions, 0 clicks, avg position 5.5.
- `링크모음 웹사이트`: 2 impressions, 1 click, avg position 144.5.
- `링크위키`: 48 impressions, 20 clicks, avg position 3.6 (brand; not a target KPI).

Main `/directory` page was crawled by Googlebot on Nov 8, with self canonical selected, but not indexed. Distinct title and description were published Nov 9. This report does not claim post-edit Google crawling or ranking impact.

## Competitor features observed in public web search (not verified rankings)
- https://hyunara.com/ — broad directory taxonomy, explicit claimed date of checks, large entry inventory. Claims are self-reported and not independently validated.
- https://2korea.net/링크모음 — category-specific use case and status labels.
- https://sitenara.net/ — multi-category directory with links to utility sections.

Do not copy competitor text, claim comparable verification, inflate directory entries, or publish fake last-checked dates.

## Actions implemented

1. Kept all three **exact keyword** queries and their existing 7-day GSC comparisons unchanged.
2. Added separate `FAMILY_QUERY_FILTERS` to `seo/search_console_monitor.py`, retrieving phrase-containing related searches without replacing exact matches.
3. Added `format_core_family_keyword_report`: for each keyword, display exact vs related impressions/clicks/weighted position in separate columns; a multi-family query is assigned to only one group to avoid double counting.
4. Dedicated API failures show as **retrieval error**, not zero impressions. Missing query rows show **not observed**, not zero search demand.
5. Added regression tests in `tests/test_search_console_monitor.py` for exact/related weighted positions, disjoint totals, regex shapes and API error semantics.

Final GitHub build QA for this code: https://github.com/a01088293068-ui/link/actions/runs/42572027261 (success).
The new GSC API execution is separate: its workflow must complete before claiming live family totals.

## What remains unproven

- Any ranking improvement resulting from today's content/link/code changes.
- Google indexing of `/directory` after the Nov 9 edit.
- Whether URLs newly seen by Google outperform homepage for exact terms.

Keep existing sitemap v2 configuration; its successful GSC fetch was previously established. Do not revisit the resolved sitemap issue.
