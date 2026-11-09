const test = require('node:test');
const assert = require('node:assert/strict');
const { inspectAddress } = require('../assets/address-inspector.js');

test('normal URL shows actual hostname and path without network access', () => {
  const out = inspectAddress('https://www.naver.com/search?q=주소모음');
  assert.equal(out.ok, true);
  assert.equal(out.host, 'www.naver.com');
  assert.equal(out.protocol, 'HTTPS');
  assert.equal(decodeURIComponent(out.path), '/search?q=주소모음');
  assert.match(out.note, /공식 운영/);
});

test('brand characters in subdomain or path are not interpreted as host', () => {
  assert.equal(inspectAddress('https://example.com.login-check.test/account').host,
    'example.com.login-check.test');
  assert.equal(inspectAddress('https://evil.example/path/linkwiki.info').host,
    'evil.example');
});

test('userinfo deception is warned about and host is shown correctly', () => {
  const out = inspectAddress('https://example.com@target.test/account');
  assert.equal(out.host, 'target.test');
  assert.ok(out.warnings.some(x => x.includes('@')));
});

test('Punycode and HTTP get distinct cautions', () => {
  const out = inspectAddress('http://xn--e1afmkfd.xn--p1ai/');
  assert.ok(out.warnings.some(x => x.includes('HTTP')));
  assert.ok(out.warnings.some(x => x.includes('Punycode')));
});

test('invalid schemes, malformed addresses and oversize input are refused', () => {
  for (const input of ['', 'ftp://example.com', 'javascript:alert(1)',
                       'example.com', 'https://', 'x'.repeat(2049)]) {
    assert.equal(inspectAddress(input).ok, false, input);
  }
});

test('DOM uses only text nodes, never innerHTML or network fetch', () => {
  const source = require('node:fs').readFileSync(
    require('node:path').join(__dirname, '..', 'assets', 'address-inspector.js'), 'utf8');
  assert.equal(source.includes('innerHTML'), false);
  assert.equal(source.includes('fetch('), false);
  assert.equal(source.includes('XMLHttpRequest'), false);
});
