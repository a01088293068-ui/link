/* LinkWiki two-site comparison: strictly local DOM data, no network calls.
 * Reuses the same crawlable directory cards as main search and filters. */
(function (root) {
  'use strict';

  function normalizedSite(site) {
    if (!site || typeof site !== 'object') return null;
    for (const field of ['name', 'category', 'description', 'url']) {
      if (typeof site[field] !== 'string' || !site[field].trim()) return null;
    }
    let url;
    try { url = new URL(site.url); } catch (_) { return null; }
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null;
    return {
      name: site.name.trim(), category: site.category.trim(),
      description: site.description.trim(), url: url.href, host: url.host
    };
  }

  function compareSites(left, right) {
    const a = normalizedSite(left);
    const b = normalizedSite(right);
    if (!a || !b) return { ok: false, message: '두 사이트의 등록 정보를 확인할 수 없습니다.' };
    if (a.name === b.name && a.url === b.url) {
      return { ok: false, message: '서로 다른 사이트 두 곳을 선택해 주세요.' };
    }
    return {
      ok: true,
      sites: [a, b],
      sameCategory: a.category === b.category,
      note: '서비스명·분야·설명·도메인은 링크위키 등록 항목 기준입니다. ' +
            '이 비교는 인기 순위, 추천 점수, 공식 인증 또는 실시간 접속 확인이 아닙니다.'
    };
  }

  function init(doc) {
    const form = doc.getElementById('lw-site-compare-form');
    const first = doc.getElementById('lw-site-compare-first');
    const second = doc.getElementById('lw-site-compare-second');
    const output = doc.getElementById('lw-site-compare-result');
    const cards = doc.getElementById('v6-results');
    if (!form || !first || !second || !output || !cards) return;

    const items = [...cards.querySelectorAll('article.v6-card')].map(card => {
      const name = card.querySelector('h3');
      const category = card.querySelector('small');
      const description = card.querySelector('p');
      const link = card.querySelector('a[href]');
      return name && category && description && link ? {
        name: name.textContent || '',
        category: category.textContent || '',
        description: description.textContent || '',
        url: link.href
      } : null;
    }).filter(normalizedSite);

    if (items.length < 2) return;
    for (const field of [first, second]) {
      const placeholder = doc.createElement('option');
      placeholder.value = '';
      placeholder.textContent = '사이트를 선택하세요';
      field.replaceChildren(placeholder);
      items.forEach((site, index) => {
        const option = doc.createElement('option');
        option.value = String(index);
        option.textContent = site.name + ' · ' + site.category;
        field.append(option);
      });
    }

    function message(text) {
      const p = doc.createElement('p');
      p.textContent = text;
      output.replaceChildren(p);
    }

    function makeSummary(site) {
      const article = doc.createElement('article');
      article.className = 'lw-site-compare-card';
      const heading = doc.createElement('h3');
      heading.textContent = site.name;
      article.append(heading);
      for (const [label, value] of [
        ['분야', site.category], ['등록 도메인', site.host], ['등록 설명', site.description]
      ]) {
        const p = doc.createElement('p');
        const strong = doc.createElement('strong');
        strong.textContent = label + ': ';
        p.append(strong, doc.createTextNode(value));
        article.append(p);
      }
      const link = doc.createElement('a');
      link.href = site.url;
      link.rel = 'noopener noreferrer external';
      link.target = '_blank';
      link.textContent = site.name + ' 사이트 열기';
      article.append(link);
      return article;
    }

    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!first.value || !second.value) {
        message('두 사이트를 모두 선택해 주세요.');
        return;
      }
      const one = items[Number(first.value)];
      const two = items[Number(second.value)];
      const result = compareSites(one, two);
      if (!result.ok) { message(result.message); return; }
      const grid = doc.createElement('div');
      grid.className = 'lw-site-compare-grid';
      result.sites.forEach(site => grid.append(makeSummary(site)));
      const categoryNote = doc.createElement('p');
      categoryNote.textContent = result.sameCategory
        ? '두 사이트는 등록 목록에서 같은 분야로 분류되어 있습니다.'
        : '두 사이트는 등록 목록에서 서로 다른 분야로 분류되어 있습니다.';
      const disclaimer = doc.createElement('p');
      disclaimer.textContent = result.note;
      output.replaceChildren(grid, categoryNote, disclaimer);
    });
    message('목록에 등록된 사이트 두 곳을 선택하면 각 서비스의 정보가 나란히 표시됩니다.');
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { normalizedSite, compareSites, init };
  }
  if (root && root.document) {
    if (root.document.readyState === 'loading') {
      root.document.addEventListener('DOMContentLoaded', () => init(root.document));
    } else init(root.document);
  }
})(typeof window !== 'undefined' ? window : null);
