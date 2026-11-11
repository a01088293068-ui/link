#!/usr/bin/env node
/**
 * LinkWiki single-command consent-safe submission workflow.
 * Never bypasses CAPTCHA/Google login, fabricates a contact, or auto-accepts
 * privacy/marketing terms. Only self-submits a vetted public site listing.
 * Browser profile and history stay entirely local (git-ignored).
 */
import { resolve, dirname, join, extname } from 'node:path';
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
  for (const dir of ASSET_DIRS) {
    let names=[];
    try{names=await readdir(dir,{withFileTypes:true});}catch{continue;}
    for(const entry of names){
      if(!entry.isFile() || !/\.(png|jpe?g|webp)$/i.test(entry.name))continue;
      const path=join(dir,entry.name);
      const info=await stat(path).catch(()=>null);
      if(info)files.push({path,name:entry.name,bytes:info.size,ext:extname(entry.name)});
    }
  }
  return {logo:chooseAsset(files,'logo'),screenshot:chooseAsset(files,'screenshot')};
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
  name:['Name','Your name'],product:['Startup or product name','Product Name','Website name'],
  website:['Website URL','Website Link','Website URL*'],
  email:['Email address','Email','Your email'],
  headline:['Headline'],description:['Long description','Description','Full description'],
};
async function findInput(page,key){
  // The field must have a unique, exact accessible label; no positional guessing.
  const items=[];
  for(const name of mapping[key]||[]){
    const l=page.getByLabel(name,{exact:true});
    if(await l.count()===1 && await l.isVisible() && await l.isEnabled()){
      const meta=await l.evaluate(el=>({
        tag:el.tagName.toLowerCase(),type:(el.getAttribute('type')||'text').toLowerCase(),
        name:(el.getAttribute('name')||'').toLowerCase()
      }));
      if(['input','textarea'].includes(meta.tag) &&
        ['text','url','email'].includes(meta.type) &&
        !(key!=='email'&&/(email|phone|password|username|user_id)/i.test(meta.name))){
        items.push(l);
      }
    }
  }
  if(items.length===1)return items[0];
  if(items.length>1)return null;
  // Some official forms only expose placeholders, not proper label elements.
  // Only a unique *exact* placeholder match is acceptable.
  const placeholders=[];
  for(const name of mapping[key]||[]){
    const candidate=page.getByPlaceholder(name,{exact:true});
    if(await candidate.count()===1 && await candidate.isVisible() && await candidate.isEnabled()){
      placeholders.push(candidate);
    }
  }
  return placeholders.length===1?placeholders[0]:null;
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
  const {logo,screenshot}=await findAssets();
  console.log('LinkWiki 등록 준비: 이메일 계정 사용(주소는 로그에 출력하지 않음).');
  console.log('로고 발견:',!!logo,'스크린샷 발견:',!!screenshot);
  // Request each remote site only after checking both VPN routes.
  const browser=await chromium.launch({channel:'chrome',headless:true,
    args:['--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
      '--disable-background-networking']});
  const history=await readHistory();
  try{
    for(const provider of PROVIDERS){
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
          let filled=0;
          for(const key of wanted){
            if(fields[key] && await fillField(page,key,fields[key]))filled++;
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
          const missing=wanted.length-filled+blockers.missingCount;
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
