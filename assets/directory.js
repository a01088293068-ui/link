/* Reuse all server-rendered directory cards instead of duplicating 211 entries.
 * Source cards remain indexable and usable when JavaScript is disabled.
 * Search only reorganizes already-present DOM elements; never fetches data.
 */
(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const input = byId('v6-query');
  const results = byId('v6-results');
  const tabs = byId('v6-tabs');
  const form = byId('v6-form');
  const count = byId('v6-count');
  const empty = byId('v6-empty');
  const reset = byId('reset-search');
  const heading = byId('directory-heading');
  const search = window.LinkWikiSearch;
  if (!input || !results || !tabs || !form || !count || !empty ||
      !reset || !heading || !search) return;

  // The build already checks that these cards match verified-directory.json.
  // Keep references to the original elements, including external-link semantics.
  const entries = [...results.querySelectorAll('article.v6-card')].map(card => {
    const cat = card.querySelector('small');
    const name = card.querySelector('h3');
    const description = card.querySelector('p');
    const link = card.querySelector('a[href]');
    if (!cat || !name || !description || !link) {
      throw new Error('Directory static card fields changed');
    }
    return {
      element: card,
      site: {
        category: cat.textContent.trim(),
        name: name.textContent.trim(),
        description: description.textContent.trim(),
        url: link.href,
        hasEvidence: card.dataset.sourceEvidence === 'true'
      }
    };
  });
  if (!entries.length) return;

  const categories = ['전체', '검색·포털', '영상·OTT', '커뮤니티', '만화',
                      '스포츠', 'AI 도구', '한인교민', '만화·웹툰', '금융·경제',
                      '교육·취업', '뉴스·언론', '쇼핑·가격비교', '생활·교통·여행'];
  const elements = new Map(entries.map(entry => [entry.site, entry.element]));
  let category = '전체';
  let evidenceOnly = false;

  function readURL() {
    const params = new URLSearchParams(location.search);
    category = categories.includes(params.get('category'))
      ? params.get('category') : '전체';
    evidenceOnly = params.get('source') === 'evidence';
    input.value = (params.get('q') || '').slice(0, 100);
  }

  function updateURL(push = false) {
    const url = new URL(location.href);
    if (category === '전체') url.searchParams.delete('category');
    else url.searchParams.set('category', category);
    if (input.value.trim()) url.searchParams.set('q', input.value.trim());
    else url.searchParams.delete('q');
    if (evidenceOnly) url.searchParams.set('source', 'evidence');
    else url.searchParams.delete('source');
    history[push ? 'pushState' : 'replaceState'](null, '', url);
  }

  function render() {
    const query = input.value.trim();
    const normalized = search.norm(query).replace(/\s+/g, '');
    const coreIntent = ['주소모음', '링크모음', '사이트모음'].includes(normalized);
    const selected = entries.filter(entry =>
      (category === '전체' || entry.site.category === category) &&
      (!evidenceOnly || entry.hasEvidence));
    const matched = search.sortResults(selected.map(entry => entry.site), query);
    results.replaceChildren(...matched.map(site => elements.get(site)));
    const resultLabel = evidenceOnly
      ? (query ? '‘' + query + '’ 출처 대조 검색 결과 ' : '출처 대조 기록이 있는 사이트 ')
      : coreIntent
        ? '전체 ' + (category === '전체' ? '등록 목록 ' : category + ' 목록 ')
        : query ? '‘' + query + '’ 검색 결과 ' : '등록 사이트 ';
    count.textContent = resultLabel + matched.length + '개';
    empty.hidden = matched.length !== 0;
    for (const button of tabs.children) {
      const pressed = button.dataset.sourceEvidence === 'true'
        ? evidenceOnly : button.dataset.cat === category;
      button.setAttribute('aria-pressed', String(pressed));
    }
    heading.textContent = category === '전체'
      ? '344개 사이트 주소 검색: 이름·도메인·분야별 목록'
      : category + ' 분야별 링크 찾기';
  }

  readURL();
  for (const cat of categories) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.cat = cat;
    button.textContent = cat === '만화' ? '만화 서비스'
      : cat === '만화·웹툰' ? '웹툰 플랫폼' : cat;
    button.addEventListener('click', () => {
      category = cat;
      updateURL(true);
      render();
    });
    tabs.append(button);
  }
  const evidenceButton = document.createElement('button');
  evidenceButton.type = 'button';
  evidenceButton.className = 'v6-evidence-filter';
  evidenceButton.dataset.sourceEvidence = 'true';
  const evidenceCount = entries.filter(entry => entry.hasEvidence).length;
  evidenceButton.textContent = '출처 대조 기록 ' + evidenceCount + '개';
  evidenceButton.setAttribute('aria-label',
    '출처 대조 기록이 있는 사이트만 보기 ' + evidenceCount + '개');
  evidenceButton.addEventListener('click', () => {
    evidenceOnly = !evidenceOnly;
    updateURL(true);
    render();
  });
  tabs.append(evidenceButton);
  input.addEventListener('input', () => { updateURL(); render(); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    updateURL();
    render();
    count.focus();
  });
  reset.addEventListener('click', () => {
    category = '전체';
    evidenceOnly = false;
    input.value = '';
    updateURL(true);
    render();
    input.focus();
  });
  window.addEventListener('popstate', () => { readURL(); render(); });
  render();
  // A shared search or homepage search already has a query. Preserve explicit
  // destinations such as the comparison panel when the link includes a fragment.
  if (input.value.trim() && !location.hash) count.focus();
})();
