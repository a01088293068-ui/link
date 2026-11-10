const test = require('node:test');
const assert = require('node:assert/strict');
const {norm, queryTerms, matches, sortResults, score} = require('../assets/directory-search.js');

const listings = [
  {name: '중고나라', category: '커뮤니티',
   description: '중고 물품을 사고파는 게시판', url: 'https://cafe.naver.com/joonggonara'},
  {name: 'Claude', category: 'AI 도구',
   description: '글쓰기와 문서 분석을 지원합니다', url: 'https://claude.ai/'},
  {name: '네이버', category: '검색·포털',
   description: '검색과 뉴스를 제공', url: 'https://www.naver.com/'},
];

test('Three core keywords, spaced or not, mean show the directory', () => {
  for (const phrase of ['주소모음', '링크모음', '사이트모음',
                        '주소 모음', '링크 모음', '사이트 모음']) {
    assert.deepEqual(listings.filter(site => matches(site, phrase)), listings, phrase);
  }
});

test('Generic directory term plus specific clue finds an actual listing', () => {
  assert.deepEqual(listings.filter(site => matches(site, '링크모음 AI 글쓰기'))
    .map(s => s.name), ['Claude']);
  assert.deepEqual(listings.filter(site => matches(site, '주소모음 커뮤니티 중고'))
    .map(s => s.name), ['중고나라']);
  assert.deepEqual(listings.filter(site => matches(site, '사이트 모음 검색·포털 naver.com'))
    .map(s => s.name), ['네이버']);
});

test('Multiple terms match across metadata, not only contiguous text', () => {
  assert.deepEqual(listings.filter(site => matches(site, '커뮤니티 중고'))
    .map(s => s.name), ['중고나라']);
  assert.deepEqual(listings.filter(site => matches(site, 'AI 문서'))
    .map(s => s.name), ['Claude']);
  assert.deepEqual(listings.filter(site => matches(site, '커뮤니티 AI')), []);
});

test('Whitespace and Unicode compatibility forms are normalized', () => {
  assert.equal(norm('  ＡＩ  문서   '), 'ai 문서');
  assert.deepEqual(queryTerms('주소 모음   AI   문서'), ['ai', '문서']);
  assert.ok(matches(listings[1], 'ＡＩ 문서'));
});

test('Empty and directory-only terms preserve all site records', () => {
  assert.deepEqual(listings.filter(site => matches(site, '')), listings);
  assert.deepEqual(listings.filter(site => matches(site, '링크 모음')), listings);
});

test('Exact service names appear before incidental descriptions and domains', () => {
  const entries = [
    {name: '네이버 소개', category: '안내', description: '네이버 서비스', url: 'https://info.example/'},
    {name: '네이버', category: '검색·포털', description: '포털', url: 'https://www.naver.com/'},
    {name: '검색 사이트', category: '검색·포털', description: '네이버 링크', url: 'https://search.example/'},
  ];
  assert.deepEqual(sortResults(entries, '네이버').map(x => x.name),
    ['네이버', '네이버 소개', '검색 사이트']);
  assert.ok(score(entries[1], '네이버') > score(entries[0], '네이버'));
});

test('Exact domain matches come ahead of incidental mentions and shared links', () => {
  const entries = [
    {name: '중고나라', category: '커뮤니티', description: '중고 거래', url: 'https://cafe.naver.com/joonggonara'},
    {name: '네이버', category: '검색·포털', description: '포털 서비스', url: 'https://www.naver.com/'},
  ];
  assert.deepEqual(sortResults(entries, 'naver.com').map(x => x.name),
    ['네이버', '중고나라']);
});

test('Empty and generic searches retain the existing editorial listing order', () => {
  assert.deepEqual(sortResults(listings, '').map(x => x.name), listings.map(x => x.name));
  assert.deepEqual(sortResults(listings, '사이트 모음').map(x => x.name), listings.map(x => x.name));
  assert.deepEqual(sortResults(listings, '없는 사이트'), []);
});

test('Pasted HTTPS/HTTP URLs and www-prefix resolve exact registered services', () => {
  const entries = [
    {name: '네이버', url: 'https://www.naver.com/', category: '검색·포털'},
    {name: '중고나라', url: 'https://cafe.naver.com/joonggonara', category: '커뮤니티'},
    {name: '다른 네이버 카페', url: 'https://cafe.naver.com/another', category: '커뮤니티'},
  ];
  for (const query of [
    'https://cafe.naver.com/joonggonara',
    'http://cafe.naver.com/joonggonara?utm_source=test#foo',
    'www.cafe.naver.com/joonggonara/',
  ]) {
    assert.deepEqual(sortResults(entries, query).map(x => x.name), ['중고나라'], query);
  }
  assert.deepEqual(sortResults(entries, 'https://www.naver.com/').map(x => x.name),
    ['네이버']);
  assert.deepEqual(sortResults(entries, 'https://unknown.example/').map(x => x.name), []);
});

test('Ordinary domain search still finds relevant subdomains', () => {
  assert.deepEqual(sortResults(listings, 'naver.com').map(x => x.name),
    ['네이버', '중고나라']);
});

test('Invalid URLs do not crash browser-side search', () => {
  assert.doesNotThrow(() => sortResults(listings, 'https://%bad'));
});
