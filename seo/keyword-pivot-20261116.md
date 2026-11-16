# LinkWiki keyword pivot and validation plan — 2026-11-16

## Decision

Keep the three head terms as long-term brand/category goals, but stop treating them as the only route to organic growth. Prioritize distinct, useful Korean search intents already supported by real catalogue inventory.

## New priority cluster: qualification and exam registration

| Priority | Search query | Intent | Matching page |
|---|---|---|---|
| P1 | 자격증 시험 접수 사이트 | Find the correct official registration portal | /blog/seo-20261116-korean-certification-exam-sites-guide/ |
| P1 | 국가자격 시험 접수 | Identify the official state qualification route | Same guide + /categories/education |
| P1 | 컴활 시험 접수 | Find the Korcham exam registration portal | Same guide + directory search |
| P1 | SQLD 시험 접수 | Find the DataQ registration portal | Same guide + directory search |
| P2 | 민간자격 조회 | Check registration and public accreditation status | Same guide + directory search |
| P2 | 토익 시험 접수 | Find official TOEIC schedules and registration | Same guide + directory search |
| P2 | 한국사 시험 접수 | Find the official Korean History test portal | Same guide + directory search |

Why this cluster: the intent is concrete and navigational; the directory now lists 21 education/employment services, including official Q-Net, Korcham, DataQ, Korean History, TOEIC, and private-qualification information routes. The article distinguishes national qualifications, private qualifications, and exam providers rather than publishing one thin page per keyword.

## Public SERP reconnaissance

On 2026-11-16, Korean search samples showed:
- Broad AI tools collection results include dedicated aggregators with 75, 309 and larger claimed inventories; this is not the first niche to pursue.
- Overseas Korean community collection has multiple dedicated competitors and ranking-style category pages; retain it as a supported category, but do not assume it is low-competition.
- Exam/education results are also competitive, but a narrower official registration intent can be served with verified primary destinations and practical distinctions.
- These search samples are qualitative SERP observations only. They do not establish monthly search volume, keyword difficulty, or guaranteed ranking opportunity.

## Changes made

1. Added four official Korean destinations to `assets/verified-directory.json`:
   - 대한상공회의소 자격평가사업단
   - 데이터자격검정 DataQ
   - TOEIC 공식 사이트
   - 민간자격정보서비스
2. Added matching official-source evidence records to `assets/directory-evidence.json`.
3. Published one substantial guide: `content/seo-20261116-korean-certification-exam-sites-guide.md`.
4. Added five new long-tail phrases to `seo/rank_tracker.py` and the seed keyword file.
5. Expanded the Korean keyword-cluster regression test to cover the new guide.
6. Updated the homepage's visible catalogue count from 337 to 341.

## Measurement rules

- Continue measuring exact head terms separately: 주소모음, 링크모음, 사이트모음.
- New cluster terms are tracked individually; do not combine them into head-term progress.
- Compare GSC query impressions, clicks, CTR, average position and landing page over matched date ranges.
- Track the guide's index status and query×URL alignment after Google recrawls it.
- Do not call a successful build, sitemap inclusion, URL submission, or article count a ranking improvement.
- If impressions remain absent after a meaningful crawl/measurement window, inspect actual query data and revise the target rather than generating near-duplicate pages.
