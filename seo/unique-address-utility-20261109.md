# LinkWiki — actual URL hostname utility on the primary directory (2026-11-09)

## Why this change
The goal is generic Korean queries **주소모음, 링크모음, 사이트모음**. At the latest available GSC report, exact queries had very few impressions (주소모음 1, rank 111; 링크모음 4, rank 123; 사이트모음 no reported query row). The full /directory URL was crawled on Nov 8 but remained not indexed in stored URL Inspection, before this release.

A competitor such as https://tokenbase.tech/ publishes a broader self-reported inventory (27 topics, 649 links) and HTTP status figures. That is the competitor's own claim, not an independently verified 649-site audit. Merely repeating head terms or adding unverified "latest" badges is not a meaningful differentiator.

## Implemented original user-facing feature
- Source: `assets/address-inspector.js` and `build.py::directory_address_inspector`.
- New static, crawlable explanation and **interactive actual-host breakdown** on `https://linkwiki.info/directory`. It helps users check the full actual hostname when links contain brand-looking text elsewhere, especially `https://example.com.login-check.test/account` or `https://example.com@target.test/account`.
- **Completely local:** URL parsing in the browser, no fetched URL, no server submission, no APIs and no storage.
- Output: actual browser-interpreted hostname, HTTP vs HTTPS, remaining path/query, explicit userinfo, punycode, non-HTTPS and unusual-port cautions.
- Explicitly never certifies a site's ownership, official status, live availability or security.
- Uses `textContent` and DOM text nodes for safe rendering. No raw HTML injection.
- Existing 97 cards, list filters, home title, /directory self-canonical and sitemap-v2 remain unchanged.

## Verification
- New Node.js tests include normal Korean URL, deceptive subdomains, userinfo @ spoofing, punycode, invalid schemes and DOM injection patterns.
- Python build regression requires exactly one form and one script, still 97 static cards, and no canonical switch.
- First intermediate QA failed due to a test incorrectly expecting the URL parser to retain unencoded Hangul in `URL.search`. Corrected to compare decoded search text. This was a test issue, not a user-visible bug.
- **Final build/test passed:** https://github.com/a01088293068-ui/link/actions/runs/42577808981 .
- **Final public crawlability smoke passed:** https://github.com/a01088293068-ui/link/actions/runs/42577842163 . It checks selected public content and canonical deployment parity but is **not** a complete browser clickthrough test of the new form.
- Independent text extraction of production confirms the directory title but strips JS/forms and cannot independently prove the form visible. Do not claim the extractor confirmed the interactive controls.
- Google indexing/rank impact is unmeasured; wait for post-Nov-9 crawl and comparable GSC period.

## Practical next step
Maintain a stable release for Google crawl; measure any real improvement to the three exact head terms and /directory indexing. Prioritize useful editorial references to /directory and real address-lookup demand rather than more identical directory submissions.
