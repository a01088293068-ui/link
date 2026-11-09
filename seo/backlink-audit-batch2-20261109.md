# LinkWiki backlink outreach and verification — batch 2 (2026-11-09)

Public target: https://linkwiki.info/ (distinct from the LinkWiki main service).

## New site-by-site due diligence and submissions

| Site | Result | Evidence | Follow-up |
|---|---|---|---|
| AbiLogic US | **Not submitted**: guidelines require English or region-appropriate listing; Korean directory unsuitable for selected US/English category | https://agent.tinyfish.ai/runs/dfab5a5f-8620-4454-bcf6-7d2deeded1d0 | Do not force an irrelevant category or fabricate English-only content |
| Viesearch | **No confirmed receipt**: free listing permitted, but the category selector did not register a valid category, and no confirmation appeared | https://agent.tinyfish.ai/runs/826808e5-bd49-4c91-ba54-69d2b844a3bd | Do not repeat submission until platform confirms whether it was received; site support or manual category selection needed |
| Free PR Web Directory | **Not submitted**: free relevant category exists but form CAPTCHA did not validate | https://agent.tinyfish.ai/runs/e6035224-c874-4c3d-836b-ce04f3369d0c | Human completion only; no CAPTCHA bypass |
| 247WebDirectory | **Not submitted**: site explicitly requires English-only submissions, excludes Korean-language site | https://agent.tinyfish.ai/runs/fb109437-e5a9-433c-ab72-924e2b309ad0 | Exclude from outreach |
| Internet Intro | **Not submitted**: rules explicitly exclude aggregators and directories; LinkWiki is a directory | https://agent.tinyfish.ai/runs/60697609-9dc2-4457-bb3e-d8d7b782af79 | Exclude from outreach |
| Website Unpacked | **Not submitted**: legitimate editorial site but Cloudflare Turnstile blocked the form | https://agent.tinyfish.ai/runs/58525103-f79f-4aa6-8f60-cb36abc21dea | Human verification only |
| Ignlab Launch | **Pre-existing published listing discovered**, agent-reported public href and independently rechecked by GitHub CI | https://agent.tinyfish.ai/runs/15bade6a-66a8-42ac-bd99-67644cd9398c | https://launch.ignlab.net/t/linkwiki-2 ; this is **not a new submission**, rel includes nofollow and ugc |

## Actual public backlink verification: independent GitHub Actions

- Workflow: `.github/workflows/backlink-public-monitor.yml`, runs every Monday 05:15 UTC and on monitor source updates.
- Code: `seo/backlink-public-check.py` (Python stdlib only; read-only).
- Offline tests: `tests/test_backlink_public_check.py` (5 tests). No Google SERP scraping or external form submissions.
- First successful monitored run: https://github.com/a01088293068-ui/link/actions/runs/42563995863 .
- DevElif: `public_link_found` with 2 direct anchors to https://linkwiki.info/, both `noopener noreferrer`, `meta_noindex=False`.
- Ignlab Launch: `public_link_found` with 1 direct anchor to https://linkwiki.info/, rel `noopener nofollow ugc`, `meta_noindex=False`.
- MeWebLink: `unverified`, HTTP 404. Not counted. Temporary site blocking or deletion not distinguishable from this one check.
- **Independently verified public listing pages**: 2 (one new in batch 1, one pre-existing discovered during batch 2).
- **Earlier successfully submitted but not yet published**: 3 (GainWeb, Site Promotion Directory, Launching Next receipt 177330).
- **New confirmed submissions in batch 2**: 0. An attempted registration is not a submission.
- Domain authority/ranking boost not measured or guaranteed; links that look like directory farms may be ignored or considered manipulative.

## Follow-up policy

- Do not submit duplicate links when a prior site says the target exists.
- Do not pay for SEO-passing links or place reciprocal badges simply to obtain followed links.
- Keep the brand name natural (LinkWiki/링크위키); no exact-match spam anchor text.
- Future progress: approve vs pending links from receipt / actual public URLs, and GSC query group `주소모음`, `링크모음`, `사이트모음` at comparable date ranges.
- Google search link spam policy: https://developers.google.com/search/docs/essentials/spam-policies .

## Korean-language independent listing discovery (2026-11-09)

- **OpenWebSide** Korean web service directory `https://openwebside.com/` lists LinkWiki twice:
  - `https://openwebside.com/products/757213b7-1ce9-41ed-9eb2-6bae9af82688` — longer description, links to `https://linkwiki.info/`.
  - `https://openwebside.com/products/24500655-57ec-4d21-bd3c-ef87f2b0c187` — shorter description, same outbound target.
- Pages were independently fetched with TinyFish and both contained clickable outbound `https://linkwiki.info/`; OpenWebSide is ONE referring domain (not two).
- Source language matches target audience. No additional submission made because listing already exists; duplicate should be reviewed by listing owner rather than created again.
- Add first URL to weekly backlink monitor as the preferred fuller entry; retain second URL only in evidence ledger.
- **Important**: Existing links are useful for referral discovery, but a duplicate listing, a direct href, or an `index, follow` directive alone does not prove that Google indexed the external source or counted the link for ranking.

## Additional Korean-language referring sources (2026-11-09)

- **SaaSKR** service profile: `https://saaskr.com/saas/linkwiki-info` — real public profile for LinkWiki with a canonical `/saas/linkwiki-info` and multiple direct outgoing links to `https://linkwiki.info/`. Confirmed by separate TinyFish page fetch and read-only GitHub Actions; no new submission was made.
- **VibeLabs Lab** `https://vibelabs.kr/lab` — search results mention LinkWiki, but independent page extraction did not confirm a direct `https://linkwiki.info/` anchor. Not counted.
- **OpenWebSide** `https://openwebside.com/products/757213b7-1ce9-41ed-b0d7-a807df42adf7` and `https://openwebside.com/products/24500655-57ec-4d21-bd3c-ef87f2b0c187`: earlier evidence confirmed **two listings on one referring domain**, not counted twice.

### Verified referring domains, not just raw page count

Latest independent GitHub Actions check: https://github.com/a01088293068-ui/link/actions/runs/42564967313

| Domain | Public page | Machine fetch | HTML anchor to target | rel / restriction |
|---|---|---|---|---|
| develif.com | https://develif.com/s/website-search-and-address-guides-by-linkwiki | 200 | 2 | `noopener noreferrer` (no `nofollow` in checked anchors); meta noindex false |
| launch.ignlab.net | https://launch.ignlab.net/t/linkwiki-2 | 200 | 1 | `noopener nofollow ugc`; meta noindex false |
| openwebside.com | https://openwebside.com/products/757213b7-1ce9-41ed-b0d7-a807df42adf7 | 200 | 1 | `noopener noreferrer`; meta noindex false |
| saaskr.com | https://saaskr.com/saas/linkwiki-info | 200 | 3 | `noopener noreferrer`; meta noindex false |
| meweblink.com | https://meweblink.com/website/linkwiki | HTTP 404 | unverified | Do not count |

**Current independently confirmed public referring domains: 4.** Of those, DevElif was newly submitted and published during current work; the other three were pre-existing discoveries. `nofollow/ugc` discloses link type; no claim of rank value, Google indexing, or Google crawl detection.

**Outstanding submitted pending review:** GainWeb, Site Promotion Directory, Launching Next (ID 177330). These are not publicly approved backlinks.

The confirmed `linkwiki.info` backlink is a user-facing external reference, distinct from Search Console's own Links report and from Google ranking/visibility. Verify GSC core query impressions over comparable periods to measure possible results.
