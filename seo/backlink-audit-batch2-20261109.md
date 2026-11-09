# LinkWiki backlink outreach and verification — batch 2 (2026-11-09)

Public target: https://linkwiki.info/ (distinct from the LinkWiki main service).

## New site-by-site due diligence and submissions

| Site | Result | Evidence | Follow-up |
|---|---|---|---|
| AbiLogic US | **Not submitted**: guidelines require English or region-appropriate listing; Korean directory unsuitable for selected US/English category | https://agent.tinyfish.ai/runs/dfab5a5f-8620-4454-bcf6-7d2deeded1d0 | Do not force an irrelevant category or fabricate English-only content |
| Viesearch | **No confirmed receipt**: free listing permitted, but the category selector did not register a valid category, and no confirmation appeared | https://agent.tinyfish.ai/runs/826808e5-bd49-4c91-ba54-69d2b844a3bd | Do not repeat submission until platform confirms whether it was received; site support or manual category selection needed |
| Free PR Web Directory | **Not submitted**: free relevant category exists but form CAPTCHA did not validate | https://agent.tinyfish.ai/runs/e6035224-c874-4c3d-836b-ce04f3369d0c | Human completion only; no CAPTCHA bypass |
| 247WebDirectory | **Not submitted**: site explicitly requires English-only submissions, excludes Korean-language site | https://agent.tinyfish.ai/runs/fb109437-e5a9-433c-ab72-924e2b309ad0 | Exclude from outreach |
| Internet Intro | **Submission attempt not yet confirmed** at initial report checkpoint | https://agent.tinyfish.ai/runs/60697609-9dc2-4457-bb3e-d8d7b782af79 | Await final agent result; never count queued job as submitted |
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
- **New confirmed submissions in batch 2 so far**: 0. An attempted registration is not a submission.
- Domain authority/ranking boost not measured or guaranteed; links that look like directory farms may be ignored or considered manipulative.

## Follow-up policy

- Do not submit duplicate links when a prior site says the target exists.
- Do not pay for SEO-passing links or place reciprocal badges simply to obtain followed links.
- Keep the brand name natural (LinkWiki/링크위키); no exact-match spam anchor text.
- Future progress: approve vs pending links from receipt / actual public URLs, and GSC query group `주소모음`, `링크모음`, `사이트모음` at comparable date ranges.
- Google search link spam policy: https://developers.google.com/search/docs/essentials/spam-policies .
