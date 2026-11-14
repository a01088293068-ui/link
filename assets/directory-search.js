/* Shared, deterministic directory search: browser and Node test compatible. */
(function (root) {
  'use strict';
  const CORE = new Set(['주소모음', '링크모음', '사이트모음']);
  const norm = value => String(value ?? '').normalize('NFKC')
    .toLocaleLowerCase('ko').replace(/\s+/g, ' ').trim();
  const tokens = value => norm(value)
    .replace(/(주소|링크|사이트)\s+모음/g, '$1모음')
    .replace(/[·,|]+/g, ' ')
    .split(' ').filter(Boolean);
  function queryTerms(value) {
    const words = tokens(value);
    // The three primary search intents identify the directory, not a listing.
    // Remove generic directory labels when combined with an actual site clue.
    return words.filter(word => !CORE.has(word.replace(/\s+/g, '')));
  }
  function pastedUrl(value) {
    const raw = String(value ?? '').trim();
    const explicit = /^https?:\/\//i.test(raw);
    const copiedAddress = /^(?:[a-z0-9-]+\.)+[a-z0-9-]+(?::\d+)?[/?#][^\s]*$/i.test(raw);
    if (!explicit && !copiedAddress && !/^www\./i.test(raw)) return null;
    try {
      const parsed = new URL(explicit ? raw : 'https://' + raw);
      if (parsed.username || parsed.password) return null;
      return {
        host: parsed.hostname.toLocaleLowerCase('ko').replace(/^www\./, ''),
        path: decodeURI(parsed.pathname).replace(/\/$/, '') || '/'
      };
    } catch (_) { return null; }
  }
  function matchesPastedUrl(site, parsed) {
    try {
      const url = new URL(site.url);
      const host = url.hostname.toLocaleLowerCase('ko').replace(/^www\./, '');
      const path = decodeURI(url.pathname).replace(/\/$/, '') || '/';
      return host === parsed.host && (parsed.path === '/' ||
        path === parsed.path || path.startsWith(parsed.path + '/'));
    } catch (_) { return false; }
  }
  function matches(site, searchText) {
    const pasted = pastedUrl(searchText);
    if (pasted) return matchesPastedUrl(site, pasted);
    const terms = queryTerms(searchText);
    if (!terms.length) return true;
    const haystack = norm([site.name, site.category, site.description,
      site.url].filter(Boolean).join(' '));
    return terms.every(term => haystack.includes(term));
  }
  function score(site, searchText) {
    const pasted = pastedUrl(searchText);
    if (pasted) {
      if (!matchesPastedUrl(site, pasted)) return -1;
      try {
        const url = new URL(site.url);
        const path = decodeURI(url.pathname).replace(/\/$/, '') || '/';
        return path === pasted.path ? 120 : 100;
      } catch (_) { return -1; }
    }
    const terms = queryTerms(searchText);
    if (!terms.length) return 0;
    if (!matches(site, searchText)) return -1;
    const name = norm(site.name);
    let host = '';
    try { host = norm(new URL(site.url).hostname.replace(/^www\./, '')); }
    catch (_) { host = ''; }
    const phrase = terms.join(' ');
    if (name === phrase || host === phrase || host === phrase.replace(/^www\./, '')) return 100;
    if (name.startsWith(phrase)) return 85;
    if (host.startsWith(phrase)) return 80;
    if (name.includes(phrase)) return 70;
    if (host.includes(phrase)) return 60;
    if (terms.every(term => name.includes(term))) return 50;
    if (terms.every(term => host.includes(term))) return 45;
    return 10;
  }
  function sortResults(sites, searchText) {
    return sites.map((site, index) => ({ site, index, relevance: score(site, searchText) }))
      .filter(row => row.relevance >= 0)
      .sort((a, b) => b.relevance - a.relevance || a.index - b.index)
      .map(row => row.site);
  }
  const api = { norm, queryTerms, pastedUrl, matches, score, sortResults };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.LinkWikiSearch = api;
})(typeof window !== 'undefined' ? window : globalThis);
