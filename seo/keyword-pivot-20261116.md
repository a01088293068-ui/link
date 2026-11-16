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

## Actual Google Search Console baseline (data through 2026-11-13)

The private Search Console API snapshot fetched on 2026-11-16 materially changes prioritization:

- 28-day total: 135 impressions, 40 clicks; branded queries account for 67 impressions / 25 clicks, while observed non-brand queries account for 53 impressions / 13 clicks.
- Exact core terms: `링크모음` 18 impressions / 5 clicks / average position 85.6; `주소모음` 2 / 1 / 109.0; `사이트모음` has no disclosed query row.
- In the latest 7-day window ending 2026-11-13, `링크모음` had 14 impressions / 4 clicks / average position 74.9 (Korea-only: 13 / 4 / 66.1). This is early movement, not top-page visibility.
- `주소 위키` and `주소위키` produced 22 combined observed impressions, but current SERPs show a separate established competitor brand at joosowiki.com. Do not optimize LinkWiki by impersonating or targeting that brand; treat these as brand-confusion observations and keep the LinkWiki identity clear.
- Google reports the homepage indexed and crawled on 2026-11-15. The main `/directory` URL was crawled on 2026-11-14 but remains "Crawled - currently not indexed". Category URLs and recent guides mostly return "URL is unknown to Google" in the sampled inspection set.
- GSC sitemap state: `sitemap-v2.xml` last downloaded 2026-11-12 with 49 submitted / 0 indexed; `sitemap.xml` was still pending with no download timestamp and no reported errors.
- The exam-registration guide had no disclosed GSC query rows in the 2026-11-13 data window; it is too new to judge. The next GSC run now prioritizes its URL inspection and also tracks the existing link/site comparison guide.

## Follow-up verification (2026-11-16, after the first strategy change)

- Latest GSC report (data through 2026-11-13): 28-day total 135 impressions / 40 clicks; recent 7 days 62 impressions / 13 clicks versus previous 7 days 47 / 17.
- Korea-only exact `링크모음`: 13 impressions / 4 clicks / average position 66.1 in the latest 7 days, versus 4 / 1 / 123.0 in the previous 7 days. This is a small-sample positive signal, not a ranking guarantee.
- Korea-only exact `주소모음`: 1 impression in each period, average position 107.0 in the latest 7 days; `사이트모음` remains unobserved in disclosed query rows.
- Current independent SERP sample (2026-11-16): LinkWiki was not found in the sampled results for the three core queries. The `사이트모음` sample covered all 30 organic positions; `주소모음` and `링크모음` samples were partial (28/30 and 27/30 observed positions), so those two results are not proof of absence from every unobserved position.
- The top sampled competitors for `주소모음` / `링크모음` include 주소핫, 여기여 and 호빵넷. This is a point-in-time API sample, not traffic or authority evidence.
- The live canonical sitemap currently exposes 56 extensionless canonical URLs and includes the new certification guide. The official GSC Sitemap API accepted a resubmission because the canonical sitemap had no recorded Google download. Current status is pending processing; this is not yet a Google download, discovery, indexation, or ranking result.
- Duplicate submissions while Google reports `isPending=true` are now suppressed. Sitemap recovery runs after substantive content/build/sitemap changes and skips resubmission while the existing submission is pending or has already been downloaded.
- The daily SERP tracker snapshot was successfully committed after a transient non-fast-forward push rejection was resolved by the existing rebase retry. Its current sample records no LinkWiki hit in the sampled top 30 for the three core keywords, with partial coverage noted above.

## Immediate decision

Do not publish another batch of near-duplicate keyword pages yet. The bottleneck is now the discovery/indexing of the already-published directory and category pages, plus the homepage's weak non-brand positions. Wait for the new sitemap processing and the next GSC crawl evidence before making more superficial title edits. Prioritize unique task utility, consistent canonical links, and measured query/page performance.

## Revised priority

1. **Homepage intent alignment first**: the measured non-brand opportunity is currently `링크모음`, so the homepage title, H1 and description now pair `주소모음` with `링크모음` while retaining `사이트모음` in supporting copy.
2. **Indexability over page count**: do not keep expanding the catalogue as a proxy for SEO. The directory has already been crawled but not indexed; improve its distinct editorial utility and ensure category pages expose crawlable static content and relevant guide links.
3. **Inspect pages with a reason**: daily GSC inspection now prioritizes the head-term comparison guide and the new exam guide, while retaining category coverage. Query metrics are tracked per guide rather than inferred from the SERP API.
4. **Do not confuse brand queries with generic opportunity**: avoid targeting "주소위키" as a brand keyword. The competitor's own brand is visible in current SERPs.
5. **Sitemap follow-through**: monitor whether Google downloads the current primary sitemap and rechecks the newly updated URLs. A submitted sitemap or successful HTTP fetch is not an indexing result.

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
