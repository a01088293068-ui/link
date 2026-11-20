const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync(
  require('node:path').join(__dirname, '..', 'assets', 'address-catalog-match.js'), 'utf8');

function harness(value, rows) {
  const handlers = {};
  const output = {
    children: [],
    replaceChildren(...nodes) { this.children = nodes; },
    append(node) { this.children.push(node); }
  };
  const form = { addEventListener(name, fn) { handlers[name] = fn; } };
  const input = { value };
  const document = {
    getElementById(id) {
      return id === 'lw-catalog-match-form' ? form :
        id === 'lw-catalog-match-input' ? input :
        id === 'lw-catalog-match-result' ? output : null;
    },
    createElement(tag) { return { tag, textContent: '', className: '', href: '' }; }
  };
  vm.runInNewContext(source, {
    document, URL, encodeURIComponent,
    fetch: async () => ({ ok: true, json: async () => rows })
  });
  return { submit: handlers.submit, output };
}
const rows = [
  {name: '네이버', category: '검색·포털', url: 'https://www.naver.com/'},
  {name: '중고나라', category: '커뮤니티', url: 'https://cafe.naver.com/joonggonara'}
];
const text = output => output.children.map(node => node.textContent).join('\n');

test('exact registered URL is identified by host and path without safety claims', async () => {
  const h = harness('https://cafe.naver.com/joonggonara', rows);
  await h.submit({ preventDefault() {} });
  assert.match(text(h.output), /등록된 주소와 도메인·경로가 일치/);
  assert.match(text(h.output), /중고나라/);
  assert.match(text(h.output), /안전성을 인증하거나 보증하지 않습니다/);
});

test('same host with a different path is explicitly distinguished', async () => {
  const h = harness('https://cafe.naver.com/other', rows);
  await h.submit({ preventDefault() {} });
  assert.match(text(h.output), /도메인은 같지만 경로가 다릅니다/);
  assert.match(text(h.output), /등록 경로/);
});

test('unlisted host is not automatically labeled dangerous', async () => {
  const h = harness('https://unknown.example/login', rows);
  await h.submit({ preventDefault() {} });
  assert.match(text(h.output), /일치하는 도메인을 찾지 못했습니다/);
  assert.match(text(h.output), /위험 여부를 판단하지 않습니다/);
});

test('credentials and invalid protocols are rejected', async () => {
  for (const value of ['https://user:pass@example.com/', 'javascript:alert(1)']) {
    const h = harness(value, rows);
    await h.submit({ preventDefault() {} });
    assert.match(text(h.output), /주소 형식을 확인/);
  }
});

test('uses same-origin catalog data and safe text nodes, not HTML injection', () => {
  assert.match(source, /verified-directory\.json/);
  assert.equal(source.includes('innerHTML'), false);
  assert.equal(source.includes('insertAdjacentHTML'), false);
});
