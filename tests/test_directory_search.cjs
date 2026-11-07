const test = require('node:test');
const assert = require('node:assert/strict');
const {norm, queryTerms, matches} = require('../assets/directory-search.js');

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
  assert.deepEqual(listings.filter(site => matches(site, '사이트 모음 naver.com'))
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
