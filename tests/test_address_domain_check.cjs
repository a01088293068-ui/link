const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup(cards) {
  const handlers = {};
  const output = {children: [], replaceChildren(...nodes) { this.children = nodes; }, append(node) { this.children.push(node); }};
  const input = {value: ''};
  const form = {addEventListener(name, fn) { handlers[name] = fn; }};
  const catalog = {querySelectorAll() { return cards.map(card => ({querySelector(selector) {
    if (selector === 'h3') return {textContent: card.name};
    if (selector === 'small') return {textContent: card.category};
    if (selector === 'a[href]') return {href: card.url};
    return null;
  }})); }};
  const document = {getElementById(id) {
    return {'lw-address-check-form': form, 'lw-address-check-input': input,
      'lw-address-check-result': output, 'v6-results': catalog}[id] || null;
  }, createElement(tag) { return {tag, children: [], className: '', textContent: '',
    append(node) { this.children.push(node); }}; }};
  vm.runInNewContext(fs.readFileSync(require.resolve('../assets/address-domain-check.js'), 'utf8'), {document, URL});
  return {handlers, input, output};
}
function text(node) { return [node.textContent || '', ...(node.children || []).map(text)].join(' '); }
const cards = [{name: '네이버', category: '검색·포털', url: 'https://www.naver.com/'}];
test('exact registered domain matches after www normalization', () => {
  const ui = setup(cards); ui.input.value = 'https://naver.com/path';
  ui.handlers.submit({preventDefault() {}});
  assert.match(text(ui.output.children[0]), /도메인이 일치/);
  assert.match(text(ui.output), /naver.com/);
});
test('unregistered domain is not falsely certified', () => {
  const ui = setup(cards); ui.input.value = 'https://naver-login.example/';
  ui.handlers.submit({preventDefault() {}});
  assert.match(text(ui.output), /일치하는 도메인을 찾지 못했습니다/);
  assert.match(text(ui.output), /안전성을 인증하지 않습니다/);
});
test('non-HTTPS address produces a visible warning', () => {
  const ui = setup(cards); ui.input.value = 'http://naver.com/';
  ui.handlers.submit({preventDefault() {}});
  assert.match(text(ui.output), /HTTPS가 아닌 주소/);
});
test('credentials and non-web schemes are rejected', () => {
  for (const address of ['https://user:pass@naver.com/', 'javascript:alert(1)']) {
    const ui = setup(cards); ui.input.value = address;
    ui.handlers.submit({preventDefault() {}});
    assert.match(text(ui.output), /비밀번호|http 또는 https/);
  }
});
test('internationalized punycode host is flagged', () => {
  const ui = setup(cards); ui.input.value = 'https://xn--e1afmkfd.xn--p1ai/';
  ui.handlers.submit({preventDefault() {}});
  assert.match(text(ui.output), /국제화 도메인/);
});
