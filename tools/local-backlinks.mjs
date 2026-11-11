#!/usr/bin/env node
/**
 * LinkWiki local outreach: explicit opt-in, no automated account creation or submission.
 * Session secrets remain local in a dedicated profile excluded from Git.
 *
 * Commands:
 *   node tools/local-backlinks.mjs list
 *   node tools/local-backlinks.mjs privacy
 *   node tools/local-backlinks.mjs open dreamboat --privacy-confirmed --vpn-interface utunN
 *   node tools/local-backlinks.mjs open syde --privacy-confirmed --vpn-interface utunN
 *   node tools/local-backlinks.mjs verify https://example.com/public/linkwiki --privacy-confirmed --vpn-interface utunN
 *
 * 'open' only opens the provider and prints a listing draft. Any login,
 * permission prompts, field entry, and submission are controlled by the user.
 */
import { createInterface } from 'node:readline/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { stdin, stdout } from 'node:process';
import { mkdir, chmod, readFile, writeFile } from 'node:fs/promises';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const runProcess = promisify(execFile);
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PROFILE = join(ROOT, '.local-backlink-profile');
const PRIVATE = join(ROOT, '.local-backlink-state');
const LOG = join(PRIVATE, 'results.json');

export const TARGET = 'https://linkwiki.info/';
export const SITES = Object.freeze({
  dreamboat: { url: 'https://dreamboat.kr/new', domain: 'dreamboat.kr' },
  syde: { url: 'https://syde.kr/showcase', domain: 'syde.kr' },
  disquiet: { url: 'https://disquiet.io/', domain: 'disquiet.io' },
  itjeom: { url: 'https://web-directory.itjeom.com/', domain: 'web-directory.itjeom.com' },
});
export const DRAFT = Object.freeze({
  title: '링크위키',
  url: TARGET,
  description: '링크위키는 검색·포털, 커뮤니티, AI 도구, 스포츠, 영상, 웹툰 등 여러 분야의 등록 사이트를 이름과 도메인으로 찾는 한국어 웹 디렉터리입니다. 사이트별 이용 목적과 주소를 비교하고 공식 주소 확인 가이드를 참고할 수 있습니다.',
});
export function normalizePublicUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password ||
      (url.port && url.port !== '443')) {
    throw new Error('HTTPS public URL required without credentials or non-standard port');
  }
  const h = url.hostname.toLowerCase();
  if (h === 'localhost' || /^(127|10|192|169)\./.test(h) ||
      /^172\.(1[6-9]|2\d|3[01])\./.test(h) ||
      !/^[a-z0-9.-]+\.[a-z]{2,}$/.test(h)) {
    throw new Error('Private or invalid host');
  }
  // Do not persist provider-issued login tokens, tracking parameters or fragments.
  if (url.search || url.hash) {
    throw new Error('Remove query parameters and fragments before verifying a public page');
  }
  return url.href;
}
export function isLinkwikiHref(href) {
  try {
    const u = new URL(href);
    return u.protocol === 'https:' &&
      (u.hostname === 'linkwiki.info' || u.hostname === 'www.linkwiki.info');
  } catch { return false; }
}
export function privacyNotice() {
  return [
    '개인정보 보호 안내',
    '- 별도 Chrome 프로필을 사용해 기존 브라우저 쿠키와 분리합니다.',
    '- 이 도구는 비밀번호, Google 이메일, 쿠키, 로컬 사용자명, IP를 기록하지 않습니다.',
    '- macOS 사용자명과 로컬 파일 경로를 외부 제출에 넣지 않습니다.',
    '- Playwright 자체는 실제 IP, 브라우저 특성, Google 계정을 숨기지 못합니다.',
    '- VPN을 사용해도 IP·DNS·IPv6·WebRTC 누출 가능성이 남습니다.',
    '- VPN 앱 킬 스위치와 DNS/IPv6 누출 보호를 활성화해야 합니다.',
    '- 외부 접속은 지정한 VPN 터널로 IPv4·IPv6 경로가 확인된 경우에만 허용합니다.',
    '- Google OAuth 로그인은 해당 사이트에 계정 정보가 제공될 수 있습니다.',
    '- CAPTCHA 우회, 브라우저 핑거프린트 위조, 자동 대량 제출을 하지 않습니다.',
    '- 아래 --privacy-confirmed 는 네트워크 보호를 보장하지 않으며 사용자의 확인 표시입니다.',
  ].join('\n');
}
export function parseRouteInterface(output) {
  const found = String(output).match(/^\s*interface:\s*([a-zA-Z0-9]+)\s*$/m);
  return found?.[1] || '';
}
export function expectedVpnInterface(args) {
  const index = args.indexOf('--vpn-interface');
  const value = index < 0 ? '' : args[index + 1] || '';
  if (!/^(utun\d+|tun\d+|wg\d+|ppp\d+)$/.test(value)) {
    throw new Error('VPN gate: specify --vpn-interface utunN; refusing network');
  }
  return value;
}
export function assertTunnelRoutes(expected, routes) {
  for (const [family, value] of Object.entries(routes)) {
    if (value !== expected) {
      throw new Error('VPN gate: ' + family + ' route does not use approved tunnel; refusing network');
    }
  }
  if (!routes.ipv4 || !routes.ipv6) throw new Error('VPN gate: dual stack routes unverified');
  return true;
}
async function routeFor(family, address) {
  try {
    const result = await runProcess('route', ['-n', 'get', family, address], {
      timeout: 5000, maxBuffer: 16384,
    });
    return parseRouteInterface(result.stdout);
  } catch {
    return '';
  }
}
async function requireVpn(args) {
  if (process.platform !== 'darwin') {
    throw new Error('VPN gate requires macOS route verification; refusing network');
  }
  const expected = expectedVpnInterface(args);
  const ipv4 = await routeFor('-inet', '1.1.1.1');
  const ipv6 = await routeFor('-inet6', '2606:4700:4700::1111');
  // An unavailable IPv6 route cannot be assumed safe.
  assertTunnelRoutes(expected, { ipv4, ipv6 });
}

export function hasPrivacyConsent(args) {
  return args.includes('--privacy-confirmed');
}
async function openSite(key) {
  if (!Object.hasOwn(SITES, key)) throw new Error('Unknown provider: ' + key);
  const { chromium } = await import('playwright');
  await mkdir(PROFILE, { recursive: true, mode: 0o700 });
  await chmod(PROFILE, 0o700);
  const context = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome', headless: false, acceptDownloads: false,
    permissions: [], viewport: { width: 1200, height: 800 },
    args: ['--force-webrtc-ip-handling-policy=disable_non_proxied_udp'],
  });
  const rl = createInterface({ input: stdin, output: stdout });
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(SITES[key].url, { waitUntil: 'domcontentloaded', timeout: 35000 });
    console.log('\n등록 준비:', key, '\n사이트:', SITES[key].url);
    console.log('등록명:', DRAFT.title, '\n등록 URL:', DRAFT.url,
                '\n설명:', DRAFT.description);
    console.log('기존 등록 및 로그인 상태를 확인하세요. 실제 제출은 직접 승인해야 합니다.');
    await rl.question('브라우저를 닫으려면 Enter: ');
  } finally {
    rl.close();
    await context.close();
  }
}
async function verify(url) {
  const safe = normalizePublicUrl(url);
  const { chromium } = await import('playwright');
  const browser = await chromium.launch({ channel: 'chrome', headless: true,
    args: ['--force-webrtc-ip-handling-policy=disable_non_proxied_udp'] });
  try {
    const page = await browser.newPage({ acceptDownloads: false });
    const response = await page.goto(safe, { waitUntil: 'domcontentloaded', timeout: 25000 });
    const links = await page.locator('a[href]').evaluateAll(nodes =>
      nodes.map(node => ({
        href: node.href,
        rel: node.getAttribute('rel') || '',
      })));
    const matches = links.filter(link => isLinkwikiHref(link.href));
    const robots = await page.locator('meta[name="robots"],meta[name="googlebot"]')
      .evaluateAll(nodes => nodes.map(node => node.getAttribute('content') || ''));
    const result = {
      provider_domain: new URL(safe).hostname,
      public_url: safe,
      status: response?.status() || 0,
      link_count: matches.length,
      link_rels: matches.map(l => l.rel),
      noindex: robots.some(r => /\bnoindex\b/i.test(r)),
      verified: response?.status() === 200 && matches.length > 0,
    };
    // No cookies, passwords, IP addresses, screenshots or user paths.
    await mkdir(PRIVATE, { recursive: true, mode: 0o700 });
    await chmod(PRIVATE, 0o700);
    let history = [];
    try { history = JSON.parse(await readFile(LOG, 'utf8')); } catch (e) {
      if (e.code !== 'ENOENT') throw e;
    }
    history.push(result);
    await writeFile(LOG, JSON.stringify(history, null, 2) + '\n', { mode: 0o600 });
    await chmod(LOG, 0o600);
    console.log(JSON.stringify(result, null, 2));
  } finally { await browser.close(); }
}
async function main(args) {
  const [cmd, arg] = args;
  if (cmd === 'list') {
    for (const [key, entry] of Object.entries(SITES)) console.log(key, entry.url);
    return;
  }
  if (!cmd || cmd === 'privacy') { console.log(privacyNotice()); return; }
  if (!['open', 'verify'].includes(cmd)) throw new Error('Unknown command');
  if (!hasPrivacyConsent(args)) {
    console.log(privacyNotice());
    throw new Error('Blocked: review privacy first, then add --privacy-confirmed');
  }
  await requireVpn(args);
  if (cmd === 'open') return openSite(arg);
  if (cmd === 'verify') return verify(arg);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch(error => {
    console.error('작업 중단:', String(error.message).replace(ROOT, '[local]'));
    process.exitCode = 1;
  });
}
