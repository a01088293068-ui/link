import test from 'node:test';
import assert from 'node:assert/strict';
import {
  chooseAsset, domainInput, submissionGate, cleanHistory, finalResult, PROVIDERS,
} from '../tools/outreach-submit.mjs';

const provider=id=>PROVIDERS.find(p=>p.id===id);
test('Joinly bare host is used to avoid path validation errors',()=>{
  assert.equal(domainInput('joinly'),'linkwiki.info');
  assert.equal(domainInput('launchpedia'),'https://linkwiki.info');
});
test('only a uniquely identified logo can be uploaded',()=>{
  const files=[
    {name:'linkwiki-banner-660x106.png',bytes:40000,ext:'.png'},
    {name:'linkwiki-logo.png',bytes:50000,ext:'.png'},
    {name:'selfie.png',bytes:50000,ext:'.png'},
  ];
  assert.equal(chooseAsset(files,'logo')?.name,'linkwiki-logo.png');
  assert.equal(chooseAsset(files,'screenshot'),null);
  assert.equal(chooseAsset([...files,{name:'linkwiki-logo-2.png',bytes:45000,ext:'.png'}],'logo'),null);
  assert.equal(chooseAsset([{name:'linkwiki-logo.png',bytes:7*1024*1024,ext:'.png'}],'logo'),null);
});
test('marketing consent can never be implied from request to submit',()=>{
  assert.equal(submissionGate({provider:provider('joinly'),hasCaptcha:false,
    uncheckedRequiredCheckboxes:false,missingFields:[],missingLogo:false,
    alreadyAttempted:false}),'blocked_consent');
});
test('captcha, legal checkboxes and missing identity fields prevent submission',()=>{
  const base={provider:provider('launchpedia'),hasCaptcha:false,
    uncheckedRequiredCheckboxes:false,missingFields:[],missingLogo:false,
    alreadyAttempted:false};
  assert.equal(submissionGate({...base,hasCaptcha:true}),'blocked_captcha');
  assert.equal(submissionGate({...base,uncheckedRequiredCheckboxes:true}),'blocked_required_checkbox');
  assert.equal(submissionGate({...base,missingFields:['contact_name']}),'missing_fields');
  assert.equal(submissionGate({...base,missingLogo:true}),'missing_asset');
  assert.equal(submissionGate({...base,alreadyAttempted:true}),'skipped_previous_attempt');
  assert.equal(submissionGate(base),'ready');
});
test('no private email, filepath or cookies in recorded submission statuses',()=>{
  const rows=cleanHistory([
    {provider:'phyco',status:'submitted_unverified',date:'2026-11-11',
      email:'private@example.com',path:'/Users/private/Desktop/private.png',cookie:'secret'},
    {provider:'other',status:'submitted_unverified',date:'2026-11-11'},
  ]);
  assert.deepEqual(rows,[{provider:'phyco',status:'submitted_unverified',date:'2026-11-11'}]);
  assert.doesNotMatch(JSON.stringify(rows),/private|secret|@/);
});
test('only observed result can count as submitted, never guaranteed backlink',()=>{
  assert.equal(finalResult('https://launchpedia.co/submit/','https://launchpedia.co/thanks/','Thank you'),'submitted_unverified');
  assert.equal(finalResult('https://launchpedia.co/submit/','https://launchpedia.co/submit/','Try again'),'submission_unconfirmed');
  assert.equal(finalResult('https://launchpedia.co/submit/','https://elsewhere.example/','No confirmation'),'submission_unconfirmed');
});
