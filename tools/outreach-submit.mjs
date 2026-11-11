#!/usr/bin/env node
/**
 * LinkWiki single-command consent-safe submission workflow.
 * Never bypasses CAPTCHA/Google login, fabricates a contact, or auto-accepts
 * privacy/marketing terms. Only self-submits a vetted public site listing.
 * Browser profile and history stay entirely local (git-ignored).
 */
import { resolve, dirname, join, extname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readdir, stat, readFile, writeFile, mkdir, chmod } from 'node:fs/promises';
import { homedir } from 'node:os';
import { requireVpn, hasPrivacyConsent } from './local-backlinks.mjs';

const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const LOCAL=join(ROOT,'.local-backlink-state');
const HISTORY=join(LOCAL,'submission-attempts.json');
const ASSET_DIRS=[join(homedir(),'Downloads'),join(homedir(),'Desktop')];
export const CONTACT_EMAIL=(process.env.LINKWIKI_OUTREACH_EMAIL||'').trim();
export const CONTACT_NAME=(process.env.LINKWIKI_CONTACT_NAME||'').trim();
export const WEBSITE='https://linkwiki.info';
const DESCRIPTION='LinkWiki is a Korean web directory that helps people discover useful websites and links. Users can browse categorized listings for search, online communities, AI tools, sports, entertainment and other web resources. LinkWiki provides a searchable interface in Korean for exploring website names, descriptions and official addresses.';
export const PROVIDERS=Object.freeze([
  {id:'joinly',url:'https://joinly.xyz/submit-startup',host:'joinly.xyz',
   requiresLogo:true,needsMarketingConsent:true},
  {id:'launchpedia',url:'https://launchpedia.co/submit/',host:'launchpedia.co',
   requiresLogo:false,needsMarketingConsent:false},
  {id:'phyco',url:'https://phyco.org/submit',host:'phyco.org',
   requiresLogo:true,needsMarketingConsent:false},
]);
export function chooseAsset(files,kind) {
  const good=files.filter(x=>/^(png|jpg|jpeg|webp)$/i.test(x.ext.replace(/^\./,'')) &&
      x.bytes>1000 && x.bytes<5*1024*1024);
  const scored=good.map(x=>{
    const n=x.name.toLowerCase();
    const brand=/(linkwiki|링크위키)/i.test(n)?10:0;
    const role=kind==='logo' ? (/(logo|로고|icon|아이콘)/i.test(n)?6:0) :
      (/(screenshot|capture|화면|스크린샷)/i.test(n)?6:0);
    const banner=/(banner|배너|contact|문의)/i.test(n)?-10:0;
    return {item:x,score:brand+role+banner};
  }).filter(x=>x.score>=16).sort((a,b)=>b.score-a.score || a.item.name.localeCompare(b.item.name));
  if (!scored.length || (scored[1] && scored[0].score===scored[1].score)) return null;
  return scored[0].item;
}
export async function findAssets() {
  const files=[];
  let seen=0;
  const ignored=/^(node_modules|\.git|\.local-backlink-profile|\.local-backlink-state|Library|backups|\.DS_Store)$/i;
  async function scan(dir,prefix='',depth=0){
    if(depth>4||seen>4000)return;
    let entries=[];
    try{entries=await readdir(dir,{withFileTypes:true});}catch{return;}
    for(const entry of entries){
      if(++seen>4000)break;
      if(entry.isSymbolicLink()||ignored.test(entry.name))continue;
      if(entry.isDirectory()){
        // Traverse only folders likely to store website deliverables. Avoid
        // unrelated private photos, system files, or a whole project checkout.
        const related=/(linkwiki|링크위키|assets|images|이미지|로고|logo|design|디자인|배너|banner|public|screenshots|스크린샷)/i;
        if(related.test(entry.name) || (depth===0 && /^(Downloads|Desktop)$/.test(basename(dir)))) {
          await scan(join(dir,entry.name),prefix+entry.name+' ',depth+1);
        }
      }else if(entry.isFile()&&/\.(png|jpe?g|webp)$/i.test(entry.name)){
        const path=join(dir,entry.name);
        const info=await stat(path).catch(()=>null);
        if(info)files.push({path,name:prefix+entry.name,bytes:info.size,ext:extname(entry.name)});
      }
    }
  }
  for(const dir of ASSET_DIRS)await scan(dir);
  return {
    logo:chooseAsset(files,'logo'),
    screenshot:chooseAsset(files,'screenshot'),
    candidates: files.filter(f=>/(linkwiki|링크위키)/i.test(f.name)).length,
    filesScanned:files.length,
  };
}

export function cleanHistory(rows) {
  const allowed=new Set(['submitted_unverified','submission_unconfirmed','blocked_consent',
    'blocked_captcha','missing_fields','missing_asset','form_changed','navigation_failed',
    'blocked_required_checkbox','skipped_previous_attempt','prepared_only']);
  return rows.filter(r=>PROVIDERS.some(p=>p.id===r.provider)).slice(-60).map(r=>({
    provider:r.provider,
    status:allowed.has(r.status)?r.status:'submission_unconfirmed',
    date:/^\d{4}-\d{2}-\d{2}$/.test(r.date||'')?r.date:'',
    // Raw HTML, URLs containing tokens, email, paths, cookies must never be logged.
  }));
}
async function readHistory(){
  try{return cleanHistory(JSON.parse(await readFile(HISTORY,'utf8')))}
  catch(e){if(e.code==='ENOENT')return [];throw e;}
}
async function writeHistory(rows){
  await mkdir(LOCAL,{recursive:true,mode:0o700});await chmod(LOCAL,0o700);
  await writeFile(HISTORY,JSON.stringify(cleanHistory(rows),null,2)+'\n',{mode:0o600});
  await chmod(HISTORY,0o600);
}
export function parseProviderFilter(args){
  const i=args.indexOf('--only');
  if(i<0)return PROVIDERS;
  const selected=(args[i+1]||'').split(',').filter(Boolean);
  if(!selected.length||selected.some(id=>!PROVIDERS.some(p=>p.id===id)))
    throw new Error('Unknown --only target. Allowed: joinly,launchpedia,phyco');
  return PROVIDERS.filter(p=>selected.includes(p.id));
}
export function domainInput(site){return site==='joinly'?'linkwiki.info':WEBSITE}
export function submissionGate({provider,hasCaptcha,uncheckedRequiredCheckboxes,missingFields,
  missingLogo,alreadyAttempted,explicitMarketingConsent=false}){
  if(alreadyAttempted)return 'skipped_previous_attempt';
  if(provider.needsMarketingConsent && !explicitMarketingConsent)return 'blocked_consent';
  if(hasCaptcha)return 'blocked_captcha';
  if(uncheckedRequiredCheckboxes)return 'blocked_required_checkbox';
  if(missingLogo)return 'missing_asset';
  if(missingFields.length)return 'missing_fields';
  return 'ready';
}
const mapping={
  name:['Name','Your name'],
  product:['Startup or product name','Product Name','Website name','Startup name'],
  website:['Website URL','Website Link','Website','Product URL'],
  email:['Email address','Email','Your email'],
  headline:['Headline'],
  description:['Long description','Description','Full description'],
};
export function normalizedFieldToken(s){
  return String(s||'').toLowerCase().normalize('NFKC').replace(/[\s_\-:*]+/g,' ').trim();
}
export function uniqueFieldIndex(controls, aliases, key) {
  const names=new Set(aliases.map(normalizedFieldToken));
  // 1) Prefer actual label / placeholder / ARIA name over HTML names.
  // 2) Every chosen field is constrained to the provider's form.
  // 3) Never infer that contact Name means project name.
  const strong=[];
  for(let i=0;i<controls.length;i++){
    const c=controls[i];
    if(!['input','textarea'].includes(c.tag) ||
      !['text','url','email','textarea'].includes(c.type) ||
      c.disabled||!c.visible)continue;
    if(key==='email' && c.type!=='email' && !/email/i.test(c.name||''))continue;
    if(key!=='email' && c.type==='email')continue;
    if(names.has(normalizedFieldToken(c.label))||
      names.has(normalizedFieldToken(c.placeholder))||
      names.has(normalizedFieldToken(c.aria)))strong.push(i);
  }
  if(strong.length===1)return strong[0];
  if(strong.length>1)return -1;
  const weak=[];
  for(let i=0;i<controls.length;i++){
    const c=controls[i];
    if(!['input','textarea'].includes(c.tag)||c.disabled||!c.visible||
      !['text','url','email','textarea'].includes(c.type))continue;
    if(key==='email' && c.type!=='email' && !/email/i.test(c.name||''))continue;
    if(key!=='email' && c.type==='email')continue;
    if(names.has(normalizedFieldToken(c.name))||names.has(normalizedFieldToken(c.id))){
      weak.push(i);
    }
  }
  return weak.length===1?weak[0]:-1;
}
/**
 * Match a text field by its visible, nearby title without depending on the
 * author's HTML <label for>. E.g. some site builders render:
 *   <div class="field"><div>Product Name</div><input ...></div>
 * Refuses ambiguous, hidden, sensitive or multiform matches.
 */
export function indexFromFieldGroups(groups, aliases, key){
  const expected=new Set(aliases.map(normalizedFieldToken));
  const matched=[];
  for(let i=0;i<groups.length;i++){
    const g=groups[i], type=g.type||'text';
    if(!g.visible||g.disabled||!['text','email','url','textarea'].includes(type))continue;
    const identity=/(password|phone|username|user_id|search|coupon|affiliate)/i.test(
      [g.name,g.id,g.autocomplete].join(' '));
    if(identity)continue;
    if(key!=='email'&&type==='email')continue;
    const exact=[g.label,g.placeholder,g.aria,g.nearby,g.name,g.id]
      .some(s=>expected.has(normalizedFieldToken(s)));
    // E-mail label may use text input; require nearby explicit email title.
    if(key==='email'&&!exact)continue;
    if(exact)matched.push(i);
  }
  return matched.length===1?matched[0]:-1;
}
async function findInput(page,key){
  // DOM-only metadata, never read field values or private content.
  // Include inputs outside <form>; Elementor/React sometimes renders forms
  // without semantic form wrappers.
  const items=page.locator('input,textarea');
  const fields=await items.evaluateAll(nodes=>nodes.map(el=>{
    const rect=el.getBoundingClientRect();
    const label=el.labels?.[0]?.textContent?.trim()||'';
    let nearby='';
    let parent=el.parentElement;
    for(let depth=0;parent&&depth<5;parent=parent.parentElement,depth++){
      // Only read nearby captions if this group owns *one* visible data
      // control, otherwise text may describe a different person's fields.
      const controls=[...parent.querySelectorAll('input,textarea')]
        .filter(n=>n.getBoundingClientRect().width>0&&n.getBoundingClientRect().height>0);
      if(controls.length!==1||controls[0]!==el)continue;
      const captions=[...parent.querySelectorAll('label,span,p,div,strong,small')]
        .filter(n=>!n.querySelector('input,textarea,button,select'))
        .map(n=>(n.textContent||'').replace(/\*/g,'').trim())
        .filter(s=>s.length>0&&s.length<50);
      const headings=[...new Set(captions.filter(s=>/^(name|your name|email|product name|website link|website url|startup or product name)$/i.test(s)))];
      if(headings.length===1){nearby=headings[0];break;}
    }
    return {
      tag:el.tagName.toLowerCase(),
      type:el.tagName==='TEXTAREA'?'textarea':(el.getAttribute('type')||'text').toLowerCase(),
      label,nearby,placeholder:el.getAttribute('placeholder')||'',
      aria:el.getAttribute('aria-label')||'',
      name:el.getAttribute('name')||'',id:el.id||'',
      autocomplete:el.getAttribute('autocomplete')||'',
      visible:rect.width>0&&rect.height>0&&getComputedStyle(el).visibility!=='hidden',
      disabled:el.disabled,
    };
  }));
  const matched=indexFromFieldGroups(fields,mapping[key]||[],key);
  return matched>=0?items.nth(matched):null;
}

async function fillField(page,key,value){
  const field=await findInput(page,key);
  if(!field)return false;
  const previous=await field.inputValue();
  if(previous.trim() && previous.trim()!==value)return false;
  if(!previous)await field.fill(value);
  return true;
}

async function checkBlockers(page){
  return await page.evaluate(()=>{
    const captcha=!!document.querySelector(
      'iframe[src*="recaptcha"],iframe[src*="hcaptcha"],iframe[src*="challenges.cloudflare.com"],[class*="captcha"],[id*="captcha"]');
    const missing=[];
    let unchecked=false;
    for(const el of document.querySelectorAll('input[required],textarea[required],select[required]')){
      if(el.disabled || el.closest('[hidden]'))continue;
      if(el.type==='checkbox'||el.type==='radio'){if(!el.checked)unchecked=true;}
      else if(!el.value?.trim())missing.push((el.getAttribute('name')||el.id||el.tagName).slice(0,45));
    }
    return {captcha,unchecked,missingCount:missing.length};
  });
}
export function finalResult(beforeUrl,afterUrl,bodyText){
  if(/thank you|submission received|successfully submitted|thanks for submitting|we received your|제출 완료/i.test(bodyText.slice(0,1400)))return 'submitted_unverified';
  if(new URL(beforeUrl).origin!==new URL(afterUrl).origin)return 'submission_unconfirmed';
  if(afterUrl!==beforeUrl)return 'submitted_unverified';
  return 'submission_unconfirmed';
}
async function operate(args) {
  if(!hasPrivacyConsent(args))throw Error('privacy confirmation required');
  await requireVpn(args);
  const submit=args.includes('--submit');
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(CONTACT_EMAIL))throw Error('LINKWIKI_OUTREACH_EMAIL env is required');
  if(CONTACT_NAME && CONTACT_NAME.length>100)throw Error('LINKWIKI_CONTACT_NAME too long');
  const {chromium}=await import('playwright');
  const {logo,screenshot,candidates,filesScanned}=await findAssets();
  console.log('LinkWiki 등록 준비: 이메일 계정 사용(주소는 로그에 출력하지 않음).');
  console.log('이미지 탐색:',filesScanned,'개 / 링크위키 관련 후보:',candidates,'개 / 로고:',!!logo,'/ 화면:',!!screenshot);
  // Request each remote site only after checking both VPN routes.
  const browser=await chromium.launch({channel:'chrome',headless:true,
    args:['--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
      '--disable-background-networking']});
  const history=await readHistory();
  try{
    for(const provider of parseProviderFilter(args)){
      const attempted=history.some(r=>r.provider===provider.id &&
        ['submitted_unverified','submission_unconfirmed'].includes(r.status));
      let state='navigation_failed';
      const context=await browser.newContext({permissions:[],acceptDownloads:false,
        serviceWorkers:'block'});
      await context.route('**/*',async route=>{
        try{await requireVpn(args);await route.continue()}
        catch{await route.abort('blockedbyclient')}
      });
      try{
        await requireVpn(args);
        const page=await context.newPage();
        const response=await page.goto(provider.url,{waitUntil:'domcontentloaded',timeout:22000});
        if(!response || response.status()>=400 ||
          ![provider.host,'www.'+provider.host].includes(new URL(page.url()).hostname)){
          state='navigation_failed';
        }else{
          const fields={
            name:CONTACT_NAME,product:'LinkWiki',website:domainInput(provider.id),email:CONTACT_EMAIL,
            headline:'Discover Korean websites and useful links in one place',
            description:DESCRIPTION
          };
          // Name field is an individual contact; no fabricated legal name.
          const wanted=provider.id==='launchpedia'?['name','product','website','email']:
            provider.id==='joinly'?['product','website','email','headline','description']:
              ['product','website','email','description'];
          const missingKeys=[];
          let filled=0;
          for(const key of wanted){
            if(fields[key] && await fillField(page,key,fields[key]))filled++;
            else missingKeys.push(key);
          }
          // Do not upload a wide banner or any unrecognized personal photo.
          if(provider.requiresLogo && logo){
            const inputs=page.locator('input[type="file"]');
            if(await inputs.count()===1 &&
              await inputs.first().isEnabled()){
              await inputs.first().setInputFiles(logo.path).catch(()=>{});
            }
          }
          const blockers=await checkBlockers(page);
          const missing=missingKeys.length+blockers.missingCount;
          if(missingKeys.length)console.log(provider.id,'찾지 못한 필드:',missingKeys.join(','));
          const gate=submissionGate({
            provider,hasCaptcha:blockers.captcha,
            uncheckedRequiredCheckboxes:blockers.unchecked,
            missingFields:missing?['required']:[],
            missingLogo:provider.requiresLogo&&!logo,
            alreadyAttempted:attempted,
          });
          if(gate==='ready'&&!submit)state='prepared_only';
          else if(gate!=='ready')state=gate;
          else{
            // A known site's exact submit button only, never an arbitrary link.
            const button=page.getByRole('button',{name:/^(submit|submit your website|submit product)$/i});
            if(await button.count()===1&&await button.isEnabled()){
              const before=page.url();
              // Click *once*. Even if outcome is uncertain, never resend blindly.
              await button.click({timeout:8000,noWaitAfter:true});
              await page.waitForTimeout(1500);
              state=finalResult(before,page.url(),await page.locator('body').innerText());
            }else state='form_changed';
          }
        }
      }catch{state='form_changed'}
      finally{await context.close()}
      // Persist no contact values, file paths, page content or tokens.
      history.push({provider:provider.id,status:state,date:new Date().toISOString().slice(0,10)});
      await writeHistory(history);
      console.log(provider.id,':',state);
    }
  }finally{await browser.close()}
  console.log('제출 후 결과는 승인/백링크 검증이 필요합니다. 사이트별 상태만 로컬 저장했습니다.');
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  operate(process.argv.slice(2)).catch(e=>{console.error('중단:',String(e.message).replace(ROOT,'[local]'));process.exitCode=1});
}
