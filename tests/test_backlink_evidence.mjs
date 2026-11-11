import test from 'node:test';
import assert from 'node:assert/strict';
import {LINK,EVIDENCE,isLinkWiki,classifyEvidence} from '../tools/backlink-evidence.mjs';
test('only the exact public SEO hostname counts',()=>{
  assert.equal(isLinkWiki(LINK),true);
  assert.equal(isLinkWiki('https://linkwiki.info'),true);
  for(const s of ['http://linkwiki.info','https://linkwiki.info.attacker.test/',
    'https://attacker.test/?next=https://linkwiki.info/',
    'https://linkwiki.info/?token=abc','https://linkwiki.info/private',
    'https://user:password@linkwiki.info/','javascript:alert(1)'])
    assert.equal(isLinkWiki(s),false);
});
test('verified public link cannot be claimed without a live href and host check',()=>{
  const valid={status:200,pageHost:'openwebside.com',expectedHost:'openwebside.com',
    links:[{href:'https://linkwiki.info/',rel:''}]};
  assert.deepEqual(classifyEvidence(valid),{status:'linked_visible_rel_not_restricted',outbound:1});
  assert.equal(classifyEvidence({...valid,links:[]}).status,'no_public_link_seen');
  assert.equal(classifyEvidence({...valid,status:403}).status,'fetch_failed');
  assert.equal(classifyEvidence({...valid,pageHost:'other.example'}).status,'untrusted_redirect');
  assert.equal(classifyEvidence({...valid,robot:'noindex'}).status,'linked_but_noindex');
  assert.equal(classifyEvidence({...valid,links:[{href:'https://linkwiki.info/',rel:'nofollow'}]}).status,'linked_nofollow_or_ugc');
});
test('public evidence hosts stay explicit and contain no credentials',()=>{
  assert.equal(EVIDENCE.length,2);
  for(const e of EVIDENCE){
    const u=new URL(e.url);
    assert.equal(u.hostname,e.host);
    assert.equal(u.protocol,'https:');
    assert.equal(u.username,'');
    assert.equal(u.search,'');
  }
});
