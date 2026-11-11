# LinkWiki Cloudflare Pages production deployment — one-time enablement

## Current confirmed state (2026-11-11)

GitHub quality gate builds **222** server-rendered directory entries and passes
393 offline regressions. The public site `https://linkwiki.info/` and
`https://linkwiki.info/directory` still showed **211** entries when last checked.

Successful GitHub builds are not Cloudflare deployments. The release-drift
workflow correctly flags production as behind source. Never claim that new
content is live based only on a GitHub CI green check.

The opt-in workflow `.github/workflows/cloudflare-pages-deploy.yml`
ran but was **skipped**, because the following opt-in condition is not
configured:

`vars.CLOUDFLARE_DEPLOY_ENABLED == 'true'`

## First establish the existing Cloudflare Pages project

Cloudflare Dashboard → Workers & Pages → the Pages project which actually has
custom domain `linkwiki.info`.

Record its exact **project name** and **account ID**. Verify its production
branch is `main`, and whether Git integration is already enabled. If
Git integration is active and configured to build `python3 build.py` into
`dist`, prefer fixing that existing deployment path to avoid duplicate
automated deployments.

Do **not** create a new Pages project or change DNS. The verifier refuses to
publish unless the configured project has `linkwiki.info` as a custom domain
and its production branch is `main`.

## Enable GitHub Actions direct deploy (optional alternative to Git build)

Create a least-privilege Cloudflare API token with Pages edit permission
for the correct account. **Never paste the token into ChatGPT, the repository,
or a committed file.**

GitHub repository Settings → Secrets and variables → Actions:

- Secrets: `CLOUDFLARE_API_TOKEN` (secret), `CLOUDFLARE_ACCOUNT_ID` (secret)
- Variables: `CLOUDFLARE_PAGES_PROJECT` (exact Pages project name)
- Variable: `CLOUDFLARE_DEPLOY_ENABLED` = `true`

These four settings are **required**. The workflow runs only for a successful
push-triggered SEO quality gate on `main`, or by explicit manual dispatch.
It builds and tests the exact commit, verifies project/domain/production-branch
with the Cloudflare API, publishes the `dist` folder via Wrangler, then
checks the public domain matches. A failure must not be reported as deployed.

Official guidance:
https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/
https://developers.cloudflare.com/pages/configuration/git-integration/

## Verification

After enabling the chosen deployment path, check GitHub Actions →
`LinkWiki Cloudflare Pages production deployment` (if using direct deploy)
and `LinkWiki live release drift audit`.

The acceptance test is **actual public site shows 222**, not that the action
was green. Recheck Google Search Console indexing and the three core queries
only after the new public build is visible.
