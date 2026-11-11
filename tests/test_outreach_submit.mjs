import test from 'node:test';
import assert from 'node:assert/strict';
import {
  chooseAsset, domainInput, submissionGate, cleanHistory, finalResult, PROVIDERS,
  uniqueFieldIndex, normalizedFieldToken, parseProviderFilter, indexFromFieldGroups, frameDecision,
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

test('LaunchPedia fields resolve by exact label or placeholder even without associated HTML label',()=>{
  const controls=[
    {tag:'input',type:'text',label:'Name',placeholder:'',aria:'',name:'contact_name',id:'',visible:true,disabled:false},
    {tag:'input',type:'email',label:'Email',placeholder:'',aria:'',name:'user_email',id:'',visible:true,disabled:false},
    {tag:'input',type:'text',label:'',placeholder:'',aria:'',name:'Product Name',id:'',visible:true,disabled:false},
    {tag:'input',type:'url',label:'Website Link',placeholder:'',aria:'',name:'site_link',id:'',visible:true,disabled:false},
    {tag:'input',type:'text',label:'Affiliate link',placeholder:'',aria:'',name:'afflink',id:'',visible:true,disabled:false},
  ];
  assert.equal(uniqueFieldIndex(controls,['Name','Your name'],'name'),0);
  assert.equal(uniqueFieldIndex(controls,['Email'],'email'),1);
  assert.equal(uniqueFieldIndex(controls,['Product Name'],'product'),2);
  assert.equal(uniqueFieldIndex(controls,['Website Link'],'website'),3);
  assert.equal(normalizedFieldToken(' Product-Name:* '),'product name');
});
test('ambiguous matches and hidden or email-mismatched fields fail closed',()=>{
  const c={tag:'input',type:'text',label:'Name',placeholder:'',aria:'',name:'name',id:'',visible:true,disabled:false};
  assert.equal(uniqueFieldIndex([c,c],['Name'],'name'),-1);
  assert.equal(uniqueFieldIndex([{...c,visible:false}],['Name'],'name'),-1);
  assert.equal(uniqueFieldIndex([c],['Email'],'email'),-1);
  assert.equal(uniqueFieldIndex([{...c,type:'email',label:'Name'}],['Name'],'name'),-1);
});

test('select a single provider without re-opening failed privacy or image-gated listings',()=>{
  assert.deepEqual(parseProviderFilter(['--only','launchpedia']).map(x=>x.id),['launchpedia']);
  assert.deepEqual(parseProviderFilter(['--only','phyco,launchpedia']).map(x=>x.id),['launchpedia','phyco']);
  assert.equal(parseProviderFilter([]).length,3);
  assert.throws(()=>parseProviderFilter(['--only','evil']),/Unknown --only target/);
  assert.throws(()=>parseProviderFilter(['--only']),/Unknown --only target/);
});

test('builder form fields work even without native label or form wrapper',()=>{
  const fields=[
    {type:'hidden',visible:false,nearby:'Name'},
    {type:'text',visible:true,disabled:false,nearby:'Name',name:'full_name'},
    {type:'text',visible:true,disabled:false,nearby:'Email',name:'contact'},
    {type:'text',visible:true,disabled:false,nearby:'Product Name',name:'item'},
    {type:'url',visible:true,disabled:false,nearby:'Website Link',name:'url'},
    {type:'text',visible:true,disabled:false,nearby:'Affiliate link',name:'affiliate'},
  ];
  assert.equal(indexFromFieldGroups(fields,['Name','Your name'],'name'),1);
  assert.equal(indexFromFieldGroups(fields,['Email','Email address'],'email'),2);
  assert.equal(indexFromFieldGroups(fields,['Product Name'],'product'),3);
  assert.equal(indexFromFieldGroups(fields,['Website Link'],'website'),4);
  assert.equal(indexFromFieldGroups([...fields,{type:'text',visible:true,nearby:'Product Name'}],['Product Name'],'product'),-1);
  assert.equal(indexFromFieldGroups([{type:'text',visible:false,nearby:'Name'}],['Name'],'name'),-1);
});

test('iframe form is only eligible when same origin and uniquely visible',()=>{
  const main={index:0,host:'launchpedia.co',visibleFields:0,captcha:false};
  const child={index:1,host:'launchpedia.co',visibleFields:5,captcha:false};
  assert.deepEqual(frameDecision('launchpedia.co',[main,child]),{status:'ready_for_field_matching',index:1});
  assert.deepEqual(frameDecision('launchpedia.co',[main]),{status:'no_rendered_fields',index:-1});
  assert.deepEqual(frameDecision('launchpedia.co',[main,{...child,host:'forms.other.example'}]),{status:'external_form_review',index:-1});
  assert.deepEqual(frameDecision('launchpedia.co',[main,{...child,captcha:true}]),{status:'blocked_captcha',index:-1});
  assert.deepEqual(frameDecision('launchpedia.co',[{...main,visibleFields:2},child]),{status:'ambiguous_multiple_frames',index:-1});
});
