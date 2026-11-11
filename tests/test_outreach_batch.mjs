import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PROVIDERS, TEXT_FIELDS, queuePlan, normalizeState,
  originAllowed, selectUniqueMatch, fieldPlan, triageTargets, classifyForm, eligibleForReview, prepareTargets,
} from '../tools/outreach-batch.mjs';

test('known submissions never return to the candidate queue', () => {
  const plan = queuePlan();
  const dreamboat = plan.find(p => p.id === 'dreamboat');
  const syde = plan.find(p => p.id === 'syde');
  assert.equal(dreamboat.status, 'skip_previously_submitted');
  assert.equal(syde.status, 'skip_previously_submitted');
  assert.ok(plan.every(p => p.url.startsWith('https://')));
  assert.equal(plan.filter(p => p.status === 'needs_form_and_contact_review').length, 3);
  assert.equal(plan.find(p => p.id === 'disquiet').status, 'skip_automation_blocked');
});
test('DNS verification is manual and must not be treated as a submitted backlink', () => {
  assert.equal(queuePlan().find(p => p.id === 'itjeom').status, 'manual_dns_verification');
});
test('safe field mappings target project data only', () => {
  assert.ok(TEXT_FIELDS.every(f => !/(email|password|nickname|username|phone)/i.test(f.key)));
  const fields = fieldPlan(['프로젝트 이름', '한 줄 소개', '프로젝트 설명','공식 사이트']);
  assert.deepEqual(fields, {name:'프로젝트 이름',short:'한 줄 소개',
    description:'프로젝트 설명',website:'공식 사이트'});
  assert.equal(fieldPlan(['한 줄 소개','한 줄 설명']).short, null);
  assert.equal(selectUniqueMatch([]), null);
  assert.equal(selectUniqueMatch(['abc']), 'abc');
  assert.equal(selectUniqueMatch(['abc', 'def']), null);
});
test('refuse untrusted provider redirects and private data URLs', () => {
  const p = PROVIDERS.find(p => p.id === 'disquiet');
  assert.equal(originAllowed('https://disquiet.io/products',p), true);
  assert.equal(originAllowed('https://accounts.disquiet.io/login',p), true);
  for (const url of [
    'http://disquiet.io/products','https://disquiet.io.attacker.test/',
    'https://attacker.test/','javascript:alert(1)',
    'https://user:pass@disquiet.io/',
  ]) assert.equal(originAllowed(url,p), false);
});
test('local ledger strips all PII, tokens, raw URLs and unsupported statuses', () => {
  const input = [
    {provider:'disquiet',status:'filled_for_review',checked_on:'2026-11-11',
      email:'private@example.org',cookies:'secret',ip:'1.2.3.4',
      page:'https://disquiet.io/?token=secret'},
    {provider:'unknown',status:'approved',url:'https://example.org/'},
    {provider:'itjeom',status:'pretend_approved',checked_on:'not-a-date'},
  ];
  const rows = normalizeState(input);
  assert.deepEqual(rows, [
    {provider:'disquiet',status:'filled_for_review',checked_on:'2026-11-11'},
    {provider:'itjeom',status:'manual_review_needed',checked_on:''},
  ]);
  assert.doesNotMatch(JSON.stringify(rows), /secret|private|1\.2\.3\.4|pretend_approved/);
});

test('captcha-blocked provider stays out of automated submission and review queue', () => {
  const p = PROVIDERS.find(x => x.id === 'disquiet');
  assert.equal(p.mode, 'blocked_human_verification');
  const candidates = PROVIDERS.filter(x => ![
    'already_submitted','requires_domain_dns_verification','blocked_human_verification'
  ].includes(x.mode));
  assert.equal(candidates.length, 5);
  const [state] = normalizeState([{provider: 'disquiet',status: 'human_verification_blocked',checked_on: '2026-11-11'}]);
  assert.equal(state.status, 'human_verification_blocked');
});

test('public triage only inspects unsubmitted locations; excludes CAPTCHA failures and previously submitted', () => {
  const ids = triageTargets().map(x=>x.id);
  assert.deepEqual(ids.sort(), ['joinly','launchpedia','phyco','startupcollections','startupstash'].sort());
  assert.equal(triageTargets().length,5);
});
test('form scan clearly separates third-party forms and anti-bot from open forms', () => {
  assert.equal(classifyForm({httpStatus:200,formFields:4,externalForm:false,antibot:false,redirectsOut:false}), 'visible_form_manual_review');
  assert.equal(classifyForm({httpStatus:200,formFields:6,externalForm:true,antibot:false,redirectsOut:false}), 'embedded_form_manual_review');
  assert.equal(classifyForm({httpStatus:200,formFields:6,externalForm:false,antibot:true,redirectsOut:false}), 'antibot_manual_review');
  assert.equal(classifyForm({httpStatus:401,formFields:0,externalForm:false,antibot:false,redirectsOut:false}), 'not_accessible');
  assert.equal(classifyForm({httpStatus:200,formFields:6,externalForm:false,antibot:false,redirectsOut:true}), 'external_redirect_manual_review');
});

test('scan classifications survive local persistence and remain distinct', () => {
  const statuses = [
    ['joinly', 'visible_form_manual_review'],
    ['launchpedia', 'visible_form_manual_review'],
    ['phyco', 'visible_form_manual_review'],
    ['startupcollections', 'embedded_form_manual_review'],
    ['startupstash', 'antibot_manual_review'],
    ['somuch', 'visible_form_manual_review'],
  ];
  const result = normalizeState(statuses.map(([provider,status])=>({
    provider,status,checked_on:'2026-11-11',account_email:'do-not-persist@example.org',
  })));
  assert.deepEqual(result.map(x=>x.status),statuses.map(x=>x[1]));
  assert.doesNotMatch(JSON.stringify(result), /do-not-persist|@example\.org/);
  const invalid = normalizeState([{provider:'joinly',status:'invented_verified_link',checked_on:'2026-11-11'}]);
  assert.equal(invalid[0].status, 'manual_review_needed');
});

test('batch review only includes public forms explicitly seen in the latest scan', () => {
  const latest = new Map([
    ['joinly','visible_form_manual_review'],
    ['launchpedia','visible_form_manual_review'],
    ['phyco','visible_form_manual_review'],
    ['startupcollections','embedded_form_manual_review'],
    ['startupstash','antibot_manual_review'],
    ['somuch','visible_form_manual_review'],
    ['disquiet','visible_form_manual_review'],
    ['dreamboat','visible_form_manual_review'],
  ]);
  const selected = eligibleForReview(PROVIDERS, latest).map(x=>x.id).sort();
  assert.deepEqual(selected,['joinly','launchpedia','phyco']);
  assert.deepEqual(eligibleForReview(PROVIDERS,new Map()),[]);
});

test('one-shot prepare excludes previously registered, CAPTCHA and policy-risk destinations', () => {
  const latest = new Map([
    ['joinly','visible_form_manual_review'],
    ['launchpedia','visible_form_manual_review'],
    ['phyco','visible_form_manual_review'],
    ['startupcollections','embedded_form_manual_review'],
    ['startupstash','antibot_manual_review'],
    ['somuch','visible_form_manual_review'],
  ]);
  assert.deepEqual(prepareTargets(PROVIDERS, latest).map(x=>x.id),
    ['joinly','launchpedia','phyco']);
  assert.equal(queuePlan().find(x=>x.id==='somuch').status, 'skip_policy_review');
  assert.deepEqual(prepareTargets(PROVIDERS,new Map()),[]);
});
