const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const search = require('../assets/directory-search.js');

const source = fs.readFileSync(path.join(__dirname, '../assets/directory.js'), 'utf8');

function makeElement(props = {}) {
  return {
    textContent: props.textContent || '',
    href: props.href,
    value: props.value || '',
    hidden: !!props.hidden,
    dataset: {},
    children: [],
    listeners: {},
    attributes: {},
    addEventListener(event, fn) { this.listeners[event] = fn; },
    setAttribute(key, value) { this.attributes[key] = value; },
    append(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    focus() { this.focused = true; }
  };
}

function makeFixture() {
  const specs = [
    ['네이버', '검색·포털', '국내 포털 서비스', 'https://www.naver.com/'],
    ['중고나라', '커뮤니티', '중고 거래 플랫폼', 'https://cafe.naver.com/joonggonara'],
    ['Claude', 'AI 도구', '문서 작성 도구', 'https://claude.ai/']
  ];
  const cards = specs.map(([name, category, description, url]) => {
    const nodes = {
      small: makeElement({textContent: category}),
      h3: makeElement({textContent: name}),
      p: makeElement({textContent: description}),
      'a[href]': makeElement({href: url})
    };
    return {querySelector(selector) { return nodes[selector]; }, identity: name};
  });
  const controls = Object.fromEntries(
    ['v6-query', 'v6-results', 'v6-tabs', 'v6-form', 'v6-count', 'v6-empty',
     'reset-search', 'directory-heading'].map(id => [id, makeElement()])
  );
  controls['v6-results'].querySelectorAll = selector => {
    assert.equal(selector, 'article.v6-card');
    return cards;
  };
  const location = {href: 'https://linkwiki.info/directory', search: ''};
  const history = {};
  for (const method of ['pushState', 'replaceState']) {
    history[method] = (state, title, url) => {
      location.href = String(url);
      location.search = new URL(location.href).search;
    };
  }
  const window = {
    LinkWikiSearch: search,
    listeners: {},
    addEventListener(name, fn) { this.listeners[name] = fn; }
  };
  const document = {
    getElementById(id) { return controls[id]; },
    createElement(tag) {
      assert.equal(tag, 'button');
      return makeElement();
    }
  };
  vm.runInNewContext(source, {document, window, history, location, URL, URLSearchParams});
  return {controls, cards, location, history, window};
}

test('directory controls are populated using the existing server HTML cards', () => {
  const {controls, cards} = makeFixture();
  assert.equal(controls['v6-results'].children.length, 3);
  assert.strictEqual(controls['v6-results'].children[0], cards[0]);
  assert.equal(controls['v6-count'].textContent, '등록 사이트 3개');
  assert.equal(controls['v6-tabs'].children.length, 9);
});

test('category filtering reuses the same cards and updates the URL', () => {
  const {controls, cards, location} = makeFixture();
  const community = controls['v6-tabs'].children.find(button =>
    button.dataset.cat === '커뮤니티');
  community.listeners.click();
  assert.equal(controls['v6-results'].children.length, 1);
  assert.strictEqual(controls['v6-results'].children[0], cards[1]);
  assert.equal(new URL(location.href).searchParams.get('category'), '커뮤니티');
  assert.equal(community.attributes['aria-pressed'], 'true');
});

test('pasted full URL filters source cards without creating replacements', () => {
  const {controls, cards, location} = makeFixture();
  const input = controls['v6-query'];
  input.value = 'https://cafe.naver.com/joonggonara';
  input.listeners.input();
  assert.strictEqual(controls['v6-results'].children[0], cards[1]);
  assert.equal(controls['v6-results'].children.length, 1);
  assert.equal(new URL(location.href).searchParams.get('q'), input.value);
  controls['reset-search'].listeners.click();
  assert.equal(controls['v6-results'].children.length, 3);
  assert.equal(new URL(location.href).searchParams.has('q'), false);
  assert.equal(input.focused, true);
});

test('explicit search focuses the results count without moving focus during typing', () => {
  const {controls} = makeFixture();
  const input = controls['v6-query'];
  const count = controls['v6-count'];
  input.value = 'Claude';
  input.listeners.input();
  assert.equal(count.focused, undefined);
  controls['v6-form'].listeners.submit({preventDefault() {}});
  assert.equal(count.focused, true);
  assert.equal(count.textContent, '‘Claude’ 검색 결과 1개');
});

test('browser back navigation restores query and category', () => {
  const {controls, window, location, cards} = makeFixture();
  location.href = 'https://linkwiki.info/directory?category=AI+%EB%8F%84%EA%B5%AC&q=Claude';
  location.search = new URL(location.href).search;
  window.listeners.popstate();
  assert.equal(controls['v6-query'].value, 'Claude');
  assert.equal(controls['v6-results'].children.length, 1);
  assert.strictEqual(controls['v6-results'].children[0], cards[2]);
});

test('JavaScript bundle has no second hardcoded list of directory sites', () => {
  assert.doesNotMatch(source, /const\s+sites\s*=\s*\[/);
  assert.match(source, /querySelectorAll\('article\.v6-card'\)/);
});
