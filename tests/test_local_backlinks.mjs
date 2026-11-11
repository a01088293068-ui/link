import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TARGET, SITES, DRAFT, isLinkwikiHref, normalizePublicUrl,
  privacyNotice, hasPrivacyConsent,
} from '../tools/local-backlinks.mjs';

test('listing only uses public SEO site, not separate service or private user details', () => {
  assert.equal(DRAFT.title, '링크위키');
  assert.equal(DRAFT.url, TARGET);
  assert.equal(TARGET, 'https://linkwiki.info/');
  assert.doesNotMatch(DRAFT.description, /linkwiki01|@|\/Users\/|password|token/i);
  assert.ok(Object.keys(SITES).length >= 4);
});
test('privacy notice states real IP cannot be concealed by Playwright', () => {
  assert.match(privacyNotice(), /실제 IP/);
  assert.match(privacyNotice(), /VPN/);
  assert.match(privacyNotice(), /Google OAuth/);
  assert.match(privacyNotice(), /자동 대량 제출/);
});
test('external commands require explicit privacy confirmation', () => {
  assert.equal(hasPrivacyConsent(['open', 'dreamboat']), false);
  assert.equal(hasPrivacyConsent(['open', 'dreamboat', '--privacy-confirmed']), true);
});
test('reject URL credentials, local destinations, and query tracking tokens', () => {
  for (const url of [
    'http://example.com/l', 'https://user:password@example.com/',
    'https://127.0.0.1/', 'https://localhost/',
    'https://192.168.0.1/a', 'https://172.20.0.1/',
    'https://example.com/public?token=secret',
    'https://example.com/public#auth',
    'https://example.com:8080/list',
  ]) {
    assert.throws(() => normalizePublicUrl(url), { name: 'Error' }, url);
  }
  assert.equal(normalizePublicUrl('https://example.com/public/linkwiki'),
    'https://example.com/public/linkwiki');
});
test('real link matches only the SEO domain, never lookalikes or HTTP', () => {
  assert.equal(isLinkwikiHref('https://linkwiki.info/'), true);
  assert.equal(isLinkwikiHref('https://linkwiki.info/directory'), true);
  assert.equal(isLinkwikiHref('https://www.linkwiki.info/'), true);
  for (const url of [
    'https://fake-linkwiki.info/', 'https://linkwiki.info.attacker.test/',
    'https://linkwiki01.com/', 'http://linkwiki.info/', 'javascript:alert(1)',
  ]) assert.equal(isLinkwikiHref(url), false);
});
