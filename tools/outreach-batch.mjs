#!/usr/bin/env node
/**
 * Batch-assisted local outreach. No hidden account creation, CAPTCHA bypass,
 * login cookie extraction, or mass unsolicited posting.
 *
 * One explicit command opens a vetted queue, fills only unambiguous text
 * fields, then waits for the account owner to inspect and submit each form.
 * Sites already registered by the owner are excluded by default.
 * Statuses saved locally never include account identifiers or cookies.
 */
import { createInterface } from 'node:readline/promises';
import { stdin, stdout } from 'node:process';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdir, chmod, readFile, writeFile } from 'node:fs/promises';
import {
  requireVpn, hasPrivacyConsent, DRAFT, TARGET, privacyNotice,
} from './local-backlinks.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PROFILE = join(ROOT, '.local-backlink-profile');
const STATE_DIR = join(ROOT, '.local-backlink-state');
const STATE_PATH = join(STATE_DIR, 'outreach-queue.json');
const MAX_ENTRIES = 100;

export const PROVIDERS = Object.freeze([
  {
    id: 'dreamboat', name: 'Dreamboat', host: 'dreamboat.kr',
    url: 'https://dreamboat.kr/new',
    alreadyPublished: 'https://dreamboat.kr/u/linkwikiinfo/p/linkwiki',
    mode: 'already_submitted',
  },
  {
    id: 'syde', name: 'SYDE 쇼케이스', host: 'syde.kr',
    url: 'https://syde.kr/showcase/create',
    mode: 'already_submitted', // user-reported, public URL not yet confirmed
  },
  {
    id: 'disquiet', name: 'Disquiet', host: 'disquiet.io',
    url: 'https://disquiet.io/products',
    mode: 'blocked_human_verification', // CAPTCHA failed in automation Chrome; don't retry
  },
  {
    id: 'itjeom', name: 'ITJEOM', host: 'web-directory.itjeom.com',
    url: 'https://web-directory.itjeom.com/',
    mode: 'requires_domain_dns_verification', // manual domain ownership proof
  },
  {
    id: 'joinly', name: 'Joinly', host: 'joinly.xyz',
    url: 'https://joinly.xyz/submit-startup',
    mode: 'public_form_needs_brand_email_and_image',
  },
  {
    id: 'launchpedia', name: 'LaunchPedia', host: 'launchpedia.co',
    url: 'https://launchpedia.co/submit/',
    mode: 'public_form_requires_contact_details',
  },
  {
    id: 'phyco', name: 'Phyco', host: 'phyco.org',
    url: 'https://phyco.org/submit',
    mode: 'public_form_needs_email_and_assets',
  },
  {
    id: 'startupcollections', name: 'Startup Collections', host: 'startupcollections.com',
    url: 'https://startupcollections.com/submit-product/',
    mode: 'embedded_form_bot_check',
  },
  {
    id: 'startupstash', name: 'Startup Stash', host: 'startupstash.com',
    url: 'https://startupstash.com/add-listing/',
    mode: 'embedded_typeform',
  },
  {
    id: 'somuch', name: 'SoMuch', host: 'somuch.com',
    url: 'https://www.somuch.com/submit-links/',
    mode: 'excluded_policy_not_verified',
  },
]);
export const TEXT_FIELDS = Object.freeze([
  {
    key: 'name', value: '링크위키 (LinkWiki)',
    labels: ['프로젝트 이름', '서비스 이름', '제품 이름', '프로덕트 이름', 'Project name', 'Product name', 'Website name', 'Startup or product name'],
  },
  {
    key: 'short', value: '주소모음·링크모음·사이트모음을 분야별로 검색하고 탐색하는 한국어 웹 디렉터리',
    labels: ['한 줄 소개', '한줄 소개', '한 줄 설명', '짧은 소개', 'Tagline', 'Short description', 'One-line description', 'Headline'],
  },
  {
    key: 'description', value: DRAFT.description,
    labels: ['프로젝트 설명', '자세한 소개', '서비스 소개', '상세 설명', '제품 설명', 'Description', 'Long description', 'Full description'],
  },
  {
    key: 'website', value: TARGET,
    labels: ['공식 사이트', '웹사이트 URL', '서비스 URL', '외부 링크', 'Website URL', 'Product URL', 'Website Link'],
  },
]);
export function queuePlan(items = PROVIDERS) {
  return items.map(({ id, name, mode, url }) => ({
    id, name, url,
    status: mode === 'already_submitted' ? 'skip_previously_submitted'
      : mode === 'requires_domain_dns_verification' ? 'manual_dns_verification'
      : mode === 'blocked_human_verification' ? 'skip_automation_blocked'
      : mode === 'excluded_policy_not_verified' ? 'skip_policy_review'
      : mode === 'embedded_form_bot_check' ? 'manual_antibot_review'
      : mode === 'embedded_typeform' ? 'third_party_form_review'
      : 'needs_form_and_contact_review',
  }));
}
export function normalizeState(input) {
  if (!Array.isArray(input)) return [];
  return input.filter(item => item && PROVIDERS.some(p => p.id === item.provider))
    .slice(-MAX_ENTRIES).map(item => ({
      provider: item.provider,
      status: ['form_detected','filled_for_review','manual_login_needed',
        'no_supported_form','already_registered','requires_domain_proof',
        'network_blocked','manual_review_needed','human_verification_blocked',
        'visible_form_manual_review','embedded_form_manual_review',
        'antibot_manual_review','not_accessible','no_visible_form',
        'external_redirect_manual_review'].includes(item.status)
        ? item.status : 'manual_review_needed',
      // No raw URL or page text: might contain personal identifiers or tokens.
      checked_on: /^\d{4}-\d{2}-\d{2}$/.test(item.checked_on) ? item.checked_on : '',
    }));
}
export async function writeState(rows) {
  await mkdir(STATE_DIR, { recursive: true, mode: 0o700 });
  await chmod(STATE_DIR, 0o700);
  await writeFile(STATE_PATH,
    JSON.stringify(normalizeState(rows), null, 2) + '\n',
    { mode: 0o600 });
  await chmod(STATE_PATH, 0o600);
}
export async function readState() {
  try { return normalizeState(JSON.parse(await readFile(STATE_PATH, 'utf8'))); }
  catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
}
export function originAllowed(url, provider) {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' &&
      (u.hostname === provider.host || u.hostname.endsWith('.' + provider.host))
      && !u.username && !u.password;
  } catch { return false; }
}
export function selectUniqueMatch(matches) {
  // Multiple matching fields can mean name vs profile-name or website vs
  // personal homepage. Ambiguous inputs must be left completely untouched.
  return matches.length === 1 ? matches[0] : null;
}
export function fieldPlan(labels, fields = TEXT_FIELDS) {
  const output = {};
  for (const field of fields) {
    const matches = labels.filter(label =>
      field.labels.some(alias => alias.toLocaleLowerCase('ko-KR') ===
        label.toLocaleLowerCase('ko-KR')));
    output[field.key] = selectUniqueMatch(matches);
  }
  return output;
}
export async function fillSafeFields(page) {
  const result = { filled: [], skipped: [], ambiguous: [] };
  // Only form controls with explicitly associated, visible, matching labels.
  // Never fill email, username, password, mobile, verification or account fields.
  for (const field of TEXT_FIELDS) {
    const candidates = [];
    for (const label of field.labels) {
      const locator = page.getByLabel(label, { exact: true });
      const count = await locator.count();
      if (count === 1) {
        const item = locator.first();
        if (await item.isVisible() && await item.isEnabled()) {
          const t = await item.evaluate(el => ({
            tag: el.tagName.toLowerCase(),
            type: (el.getAttribute('type') || '').toLowerCase(),
            name: (el.getAttribute('name') || '').toLowerCase(),
            autocomplete: (el.getAttribute('autocomplete') || '').toLowerCase(),
          }));
          const allowedTag = ['input','textarea'].includes(t.tag);
          const safeType = !t.type || ['text','url'].includes(t.type);
          const badIdentity = /(email|phone|password|username|account|user_name|nickname|identity)/i
            .test(t.name + ' ' + t.autocomplete);
          if (allowedTag && safeType && !badIdentity) candidates.push(item);
        }
      } else if (count > 1) {
        result.ambiguous.push(field.key);
      }
    }
    // Strict cardinality: if two aliases matched distinct controls, do not guess.
    // Duplicate labels can indicate a profile field instead of project data.
    if (candidates.length !== 1 || result.ambiguous.includes(field.key)) {
      result.skipped.push(field.key);
      continue;
    }
    const element = candidates[0];
    const current = await element.inputValue();
    if (current && current.trim() && current.trim() !== field.value.trim()) {
      result.skipped.push(field.key); // do not overwrite existing user data
      continue;
    }
    if (!current) await element.fill(field.value);
    result.filled.push(field.key);
  }
  return result;
}
async function guardedBrowser(args) {
  // Check traffic routes before each request; do not intentionally disable
  // Playwright security protections. Not equivalent to a VPN kill switch.
  await requireVpn(args);
  await mkdir(PROFILE, { recursive: true, mode: 0o700 });
  await chmod(PROFILE, 0o700);
  const { chromium } = await import('playwright');
  const context = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome', headless: false, permissions: [], acceptDownloads: false,
    serviceWorkers: 'block',
    args: [
      '--disable-background-networking',
      '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
    ],
    viewport: { width: 1180, height: 860 },
  });
  await context.route('**/*', async route => {
    try { await requireVpn(args); await route.continue(); }
    catch { await route.abort('blockedbyclient'); }
  });
  return context;
}
async function inspectProvider(context, provider) {
  if (provider.mode === 'already_submitted') return 'already_registered';
  if (provider.mode === 'requires_domain_dns_verification') return 'requires_domain_proof';
  if (provider.mode === 'blocked_human_verification') return 'human_verification_blocked';
  const page = context.pages()[0] || await context.newPage();
  try {
    await page.goto(provider.url, { waitUntil: 'domcontentloaded', timeout: 25000 });
    const address = page.url();
    if (!originAllowed(address, provider)) return 'manual_login_needed';
    const outcome = await fillSafeFields(page);
    console.log(provider.name, ': 작성', outcome.filled.join(', ') || '없음',
      '/ 검토 필요', outcome.skipped.join(', '));
    console.log('계정 본인이 로그인과 사이트 정책을 확인하세요.');
    console.log('이 도구는 게시 버튼을 대신 누르지 않습니다.');
    console.log('새 프로젝트 폼이 열리면 개인정보 표시 범위를 직접 확인하세요.');
    return outcome.filled.length ? 'filled_for_review' : 'no_supported_form';
  } catch (err) {
    // Preserve no page URL, IP, cookies or account info in logs.
    return 'manual_review_needed';
  } finally { /* Keep tab available for owner review; close at end of batch. */ }
}
export function eligibleForReview(providers, latest) {
  return providers.filter(item => {
    if (['already_submitted','requires_domain_dns_verification',
      'blocked_human_verification','embedded_form_bot_check',
      'embedded_typeform','excluded_policy_not_verified'].includes(item.mode)) return false;
    return latest.get(item.id) === 'visible_form_manual_review';
  });
}
/**
 * One-command safe preparation without repeated prompts: open every previously
 * scanned public form, fill only unambiguous project fields, leave all tabs
 * open until the operator presses Enter once. Never post or sign in.
 */
export function prepareTargets(providers, latest) {
  return eligibleForReview(providers, latest).filter(item =>
    !['policy_review_required','excluded_policy_not_verified'].includes(item.mode));
}
async function prepareBatch(args) {
  const latest = new Map((await readState()).map(item => [item.provider,item.status]));
  const candidates = prepareTargets(PROVIDERS, latest);
  console.log('등록 양식 준비:', candidates.length, '곳; 인증·개인정보·제출은 자동 처리하지 않습니다.');
  if (!candidates.length) return;
  const context = await guardedBrowser(args);
  const records = await readState();
  const rl = createInterface({ input: stdin, output: stdout });
  try {
    for (const item of candidates) {
      await requireVpn(args);
      const page = await context.newPage();
      let status = 'manual_review_needed';
      try {
        const response = await page.goto(item.url, {
          waitUntil: 'domcontentloaded',timeout:20000,
        });
        if (response?.status() !== 200 || !originAllowed(page.url(),item)) {
          status = 'manual_login_needed';
        } else {
          const outcomes = await fillSafeFields(page);
          status = outcomes.filled.length ? 'filled_for_review' : 'no_supported_form';
          console.log(item.name+': 작성 '+(outcomes.filled.join(', ') || '없음')+
            ' / 미작성 '+outcomes.skipped.join(', '));
        }
      } catch {
        status = 'manual_review_needed';
        console.log(item.name+': 폼 접근 실패; 수동 검토 필요');
      }
      records.push({provider:item.id,status,checked_on:new Date().toISOString().slice(0,10)});
      await writeState(records);
    }
    console.log('화면에서 연락처 공개 범위와 등록 정책을 확인하세요. 프로그램은 제출 버튼을 누르지 않았습니다.');
    await rl.question('모든 검토를 마쳤다면 Enter를 눌러 자동화 브라우저를 닫습니다: ');
  } finally {
    rl.close();
    await context.close();
  }
}
async function runBatch(args) {
  const plan = queuePlan();
  const records = await readState();
  const latest = new Map(records.map(item => [item.provider, item.status]));
  const eligible = eligibleForReview(PROVIDERS, latest);
  console.log('대상:', plan.length, '기존제출 생략:', plan.filter(x=>x.status==='skip_previously_submitted').length,
    '자동 입력 검토 후보:', eligible.length, '사람 인증 차단:', plan.filter(x=>x.status==='skip_automation_blocked').length);
  if (!eligible.length) {
    console.log('직전 공개 검사에서 안전한 일반 폼이 확인된 등록처가 없습니다. scan을 먼저 실행하세요.');
    return;
  }
  const rl = createInterface({ input: stdin, output: stdout });
  const context = await guardedBrowser(args);
  const results = records;
  try {
    for (const provider of eligible) {
      await requireVpn(args);
      const answer = (await rl.question(
        provider.name + ' 페이지를 열어 검토하겠습니까? [y/N] ')).trim().toLowerCase();
      if (answer !== 'y') continue;
      const status = await inspectProvider(context, provider);
      // Keep the browser open for owner to inspect and sign in; the
      // navigation may require account authentication or changed forms.
      await rl.question('필요한 계정 확인·직접 등록을 마친 뒤 Enter를 누르면 다음 후보로 이동합니다: ');
      results.push({ provider: provider.id, status,
        checked_on: new Date().toISOString().slice(0, 10) });
      await writeState(results);
    }
  } finally {
    rl.close();
    await context.close();
  }
  console.log('검토 기록 저장 완료 (인증·게시 여부와 무관). 등록 성공은 공개 링크 확인 후 집계하세요.');
}
export function triageTargets(items=PROVIDERS) {
  return items.filter(item => ![
    'already_submitted','requires_domain_dns_verification',
    'blocked_human_verification','excluded_policy_not_verified',
  ].includes(item.mode));
}
export function classifyForm({httpStatus, formFields, externalForm, antibot, redirectsOut}) {
  if (redirectsOut) return 'external_redirect_manual_review';
  if (antibot) return 'antibot_manual_review';
  if (!httpStatus || httpStatus >= 400) return 'not_accessible';
  if (externalForm) return 'embedded_form_manual_review';
  return formFields >= 2 ? 'visible_form_manual_review' : 'no_visible_form';
}
async function scanWithoutPosting(args) {
  // No existing login sessions, no screenshots, no user account information.
  // Each allowed provider is visited once; never click a submit element.
  const targets = triageTargets();
  const { chromium } = await import('playwright');
  await requireVpn(args);
  const browser = await chromium.launch({
    channel: 'chrome', headless: true,
    args: ['--disable-background-networking',
      '--force-webrtc-ip-handling-policy=disable_non_proxied_udp'],
  });
  const observations = [];
  try {
    for (const item of targets) {
      await requireVpn(args);
      const context = await browser.newContext({
        permissions: [], acceptDownloads: false, serviceWorkers: 'block',
      });
      await context.route('**/*', async route => {
        try { await requireVpn(args); await route.continue(); }
        catch { await route.abort('blockedbyclient'); }
      });
      const page = await context.newPage();
      let status = 'not_accessible';
      try {
        const response = await page.goto(item.url, {
          waitUntil: 'domcontentloaded', timeout: 16000,
        });
        const external = !originAllowed(page.url(), item);
        const details = await page.evaluate(() => ({
          formFields: [...document.querySelectorAll('input,textarea,select')]
            .filter(el => !['hidden','password','email'].includes(
              (el.getAttribute('type')||'').toLowerCase())).length,
          externalForm: !!document.querySelector('iframe[src*="typeform"],iframe[src*="docs.google"]'),
          antibot: !!document.querySelector('[class*="captcha"],[id*="captcha"],iframe[src*="challenges.cloudflare.com"]'),
        }));
        status = classifyForm({
          httpStatus: response?.status()||0, ...details,
          redirectsOut: external,
        });
      } catch {
        status = 'not_accessible';
      }
      observations.push({
        provider: item.id, status, checked_on: new Date().toISOString().slice(0,10),
      });
      await context.close();
      console.log(item.name + ': ' + status);
    }
  } finally {
    await browser.close();
  }
  const saved = await readState();
  await writeState([...saved, ...observations]);
  console.log('자동 진단 완료: 실제 등록이나 로그인은 수행하지 않았습니다.');
}
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'plan';
  if (command === 'plan') {
    console.log(privacyNotice());
    for (const row of queuePlan()) console.log(row.name, ':', row.status);
    return;
  }
  if (command === 'status') {
    // Latest recorded state per provider, rather than a confusing history
    // containing old entries for the same provider.
    const latest = new Map((await readState()).map(item => [item.provider, item]));
    for (const item of latest.values()) console.log(item.provider, item.status, item.checked_on);
    return;
  }
  if (!['run','scan','prepare'].includes(command)) throw new Error('Commands: plan, status, scan, prepare, run');
  if (!hasPrivacyConsent(args)) throw new Error('Need --privacy-confirmed for any external access');
  await requireVpn(args);
  if (command === 'scan') return scanWithoutPosting(args);
  if (command === 'prepare') return prepareBatch(args);
  await runBatch(args);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {
    console.error('작업 중단:', String(error.message).replace(ROOT, '[local]'));
    process.exitCode = 1;
  });
}
