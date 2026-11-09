# LinkWiki — keyword-first usable search and index evidence batch, 2026-11-09

## Baseline / unresolved issues

- Google Search Console query impressions remain sparse for the exact queries: `주소모음` 1 impression / average rank 111; `링크모음` 4 impressions / avg rank 123; `사이트모음` has no disclosed row (not proof of 0 actual searches).
- `/directory` was crawled on Nov 8 but is not indexed in the latest stored inspection. No fresh post-Nov-9 crawl has yet been confirmed. This remains unresolved.
- The separate sitemap-v2.xml had already been processed successfully. **Not modified**.
- Successful completed GSC API report (latest before changes): https://github.com/a01088293068-ui/link/actions/runs/42573104310 . Google API data continues to be delayed and should not be presented as realtime ranking.

## Actual implementation

1. `build.py::directory_search_help` now has **five** data-backed direct search examples instead of three: site names for actual listed search / AI / sports examples, and two actual registered domains. The script quotes user search values and never fabricates results or claims that a site is currently working.
2. Each example uses the existing `/directory?q=` URL interaction, not an extra indexable duplicate page. The existing page canonical remains `https://linkwiki.info/directory` and no sitemap changes were made.
3. New test in `tests/test_seo_release_regression.py` verifies all five links resolve to real registered names or real target domains, with exactly 3 name and 2 domain examples and no duplicate component.
4. Avoid overlapping expensive GSC jobs on rapid successive commits: `.github/workflows/search-console-monitor.yml` now has shared concurrency group and `cancel-in-progress: true`. One latest GSC run is preferred over parallel identical historical requests; existing schedule and manual trigger remain available.

## Proof

- Implementation commit: https://github.com/a01088293068-ui/link/commit/690c3a46577b4c0b1c41870b9548a77cd0f27dd6
- Regression commit: https://github.com/a01088293068-ui/link/commit/bed6ae71474ce408e280a225df307a192f1b612f
- Final successful GitHub SEO build QA: https://github.com/a01088293068-ui/link/actions/runs/42573912792 .
- Independently fetched production `https://linkwiki.info/directory` HTML and found five real search links:
  - `/directory?q=%EB%84%A4%EC%9D%B4%EB%B2%84` (네이버)
  - `/directory?q=ChatGPT`
  - `/directory?q=%EB%84%A4%EC%9D%B4%EB%B2%84%20%EC%8A%A4%ED%8F%AC%EC%B8%A0` (네이버 스포츠)
  - `/directory?q=www.naver.com`
  - `/directory?q=chatgpt.com`
- During intermediate implementation one QA run failed because the prior test still expected 3 links; updated test to assert 5 real links. **Final QA passed**.

## Measurement boundaries and priority

- These are genuine user-experience changes, not proven ranking increases.
- Do not report unconfirmed Google indexing or claim the `사이트모음` query had literally zero impressions.
- Track both exact target query GSC performance and `/directory` Google crawl/index status after next crawl. Keep related keyword ranks in separate columns.
- If Google still reports crawled/not indexed, evaluate unique content value and internal discovery rather than repeatedly resubmit already working sitemaps.
