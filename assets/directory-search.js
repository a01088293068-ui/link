/* Shared, deterministic directory search: browser and Node test compatible. */
(function (root) {
  'use strict';
  const CORE = new Set(['주소모음', '링크모음', '사이트모음']);
  const norm = value => String(value ?? '').normalize('NFKC')
    .toLocaleLowerCase('ko').replace(/\s+/g, ' ').trim();
  const tokens = value => norm(value).split(' ').filter(Boolean);
  function queryTerms(value) {
    const words = tokens(value);
    // The three primary search intents identify the directory, not a listing.
    // Remove generic directory labels when combined with an actual site clue.
    return words.filter(word => !CORE.has(word.replace(/\s+/g, '')));
  }
  function matches(site, searchText) {
    const terms = queryTerms(searchText);
    if (!terms.length) return true;
    const haystack = norm([site.name, site.category, site.description,
      site.url].filter(Boolean).join(' '));
    return terms.every(term => haystack.includes(term));
  }
  const api = { norm, queryTerms, matches };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.LinkWikiSearch = api;
})(typeof window !== 'undefined' ? window : globalThis);
