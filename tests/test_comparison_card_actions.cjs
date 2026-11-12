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

test('result cards retain two comparison selections across search filters', () => {
  const names = ['정부24', '국민신문고', '위택스'];
  const cards = names.map((name, i) => ({
    ...element(),
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
  let visibleCards = cards;
  controls['v6-results'] = { querySelectorAll: () => visibleCards };
  init({
    getElementById: id => controls[id],
    createElement: element,
    createTextNode: text => text,
  });

  const [first, second, third] = cards.map(card => card.children[0]);
  const output = controls['lw-site-compare-result'];
  first.events.click();
  assert.equal(first.attributes['aria-pressed'], 'true');
  assert.match(output.children[0].textContent, /정부24 선택됨/);
  visibleCards = [cards[1]];
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
  assert.equal(controls['lw-site-compare-second'].value, '');
});
