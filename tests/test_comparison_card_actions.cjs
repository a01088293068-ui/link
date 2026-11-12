const assert = require('node:assert/strict');
const test = require('node:test');
const { init } = require('../assets/site-comparison.js');

function element() {
  return {
    value: '', children: [], attributes: {}, events: {},
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    addEventListener(name, handler) { this.events[name] = handler; },
    setAttribute(name, value) { this.attributes[name] = value; },
    focus() { this.focused = true; },
  };
}

function fixture(search = '') {
  const names = ['정부24', '국민신문고', '위택스'];
  const cards = names.map((name, i) => ({
    ...element(),
    id: "site-" + i,
    querySelector(selector) {
      return {
        h3: { textContent: name },
        small: { textContent: '검색·포털' },
        p: { textContent: '등록 설명' },
        'a[href]': { href: 'https://example.org/' + i },
      }[selector];
    },
  }));
  const controls = Object.fromEntries([
    'lw-site-compare-form', 'lw-site-compare-first',
    'lw-site-compare-second', 'lw-site-compare-result',
  ].map(id => [id, element()]));
  controls['v6-results'] = { querySelectorAll: () => cards };
  init({
    location: { search },
    getElementById: id => controls[id],
    createElement: element,
    createTextNode: text => text,
  });

  return {
    buttons: cards.map(card => card.children[0]),
    output: controls['lw-site-compare-result'],
    secondField: controls['lw-site-compare-second'],
    filterToSecond() { controls['v6-results'].querySelectorAll = () => [cards[1]]; },
  };
}

test('result cards retain two comparison selections across search filters', () => {
  const { buttons: [first, second, third], output, secondField, filterToSecond } = fixture();
  first.events.click();
  assert.equal(first.attributes['aria-pressed'], 'true');
  assert.match(output.children[0].textContent, /정부24 선택됨/);
  filterToSecond();
  second.events.click();
  assert.deepEqual(output.children[0].children.map(c => c.children[0].textContent),
                   ['정부24', '국민신문고']);
  assert.equal(output.focused, true);

  third.events.click();
  assert.equal(second.attributes['aria-pressed'], 'false');
  assert.deepEqual(output.children[0].children.map(c => c.children[0].textContent),
                   ['정부24', '위택스']);
  third.events.click();
  assert.equal(third.attributes['aria-pressed'], 'false');
  assert.equal(secondField.value, '');
});

test('a preset opens the two matching catalog entries and provides a reusable link', () => {
  const { buttons, output } = fixture('?q=정부24&compare=site-0%2Csite-1');
  assert.deepEqual(output.children[0].children.map(c => c.children[0].textContent),
                   ['정부24', '국민신문고']);
  assert.equal(buttons[0].attributes['aria-pressed'], 'true');
  assert.equal(buttons[1].attributes['aria-pressed'], 'true');
  assert.equal(output.children[3].href,
               '/directory?compare=site-0%2Csite-1#directory-two-site-compare');
});

test('unknown, identical or extra preset entries leave selection controls usable', () => {
  for (const search of ['?compare=site-0,missing', '?compare=site-0,site-0',
                        '?compare=site-0,site-1,site-2']) {
    const { buttons, output } = fixture(search);
    assert.match(output.children[0].textContent, /목록에서 다시 선택/);
    buttons[0].events.click();
    buttons[1].events.click();
    assert.equal(output.children[0].children.length, 2);
  }
});
