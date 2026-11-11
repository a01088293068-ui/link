#!/usr/bin/env node
/**
 * Verify *publicly visible* LinkWiki outbound references via a fresh, isolated
 * browser. Never logs in, posts, manages cookies, or connects to admin apps.
 * Route checks are best-effort, not a VPN kill-switch guarantee.
 */
import { resolve,dirname } from 'node:path';
import {fileURLToPath} from 'node:url';
import {requireVpn,hasPrivacyConsent} from './local-backlinks.mjs';

export const LINK='https://linkwiki.info/';
export const EVIDENCE=[
  {id:'openwebside',name:'오픈웹사이드',url:'https://openwebside.com/products/757213b7-1ce9-41ed-9eb2-6bae9af82688',host:'openwebside.com'},
  {id:'dreamboat',name:'드림보트',url:'https://dreamboat.kr/u/linkwikiinfo/p/linkwiki',host:'dreamboat.kr'},
];
export function isLinkWiki(href){
  try{
    const url=new URL(href);
    return url.protocol==='https:'&&url.hostname==='linkwiki.info'&&
      !url.username&&!url.password&&url.search===''&&
      (url.pathname==='/'||url.pathname==='');
  }catch{return false}
}
export function classifyEvidence({status,links=[],robot='',pageHost='',expectedHost=''}){
  if(status>=400||status<200)return {status:'fetch_failed',outbound:0};
  if(pageHost!==expectedHost && pageHost!=='www.'+expectedHost)
    return {status:'untrusted_redirect',outbound:0};
  const matched=links.filter(l=>isLinkWiki(l.href));
  if(!matched.length)return {status:'no_public_link_seen',outbound:0};
  const nofollow=matched.every(l=>/(\bnofollow\b|\bsponsored\b|\bugc\b)/i.test(l.rel||''));
  if(/noindex/i.test(robot))return {status:'linked_but_noindex',outbound:matched.length};
  return {status:nofollow?'linked_nofollow_or_ugc':'linked_visible_rel_not_restricted',
    outbound:matched.length};
}
async function inspect(page,entry){
  let response;
  try{response=await page.goto(entry.url,{waitUntil:'domcontentloaded',timeout:20000})}
  catch{return {status:'fetch_failed',outbound:0}}
  await page.waitForTimeout(1000);
  const data=await page.evaluate(()=>({
    links:[...document.querySelectorAll('a[href]')].map(a=>({
      href:a.href,rel:a.rel||''
    })).filter(l=>{try{return new URL(l.href).hostname==='linkwiki.info'}catch{return false}}),
    robot:document.querySelector('meta[name="robots"]')?.getAttribute('content')||''
  }));
  return classifyEvidence({status:response?.status()||0,links:data.links,
    robot:data.robot,pageHost:new URL(page.url()).hostname,
    expectedHost:entry.host});
}
async function main(args){
  if(!hasPrivacyConsent(args))throw Error('Need --privacy-confirmed');
  await requireVpn(args);
  const {chromium}=await import('playwright');
  const browser=await chromium.launch({channel:'chrome',headless:true,
    args:['--disable-background-networking',
      '--force-webrtc-ip-handling-policy=disable_non_proxied_udp']});
  try{
    for(const entry of EVIDENCE){
      await requireVpn(args);
      const context=await browser.newContext({serviceWorkers:'block',
        acceptDownloads:false,permissions:[]});
      await context.route('**/*',async route=>{
        try{await requireVpn(args);await route.continue()}
        catch{await route.abort('blockedbyclient')}
      });
      try{
        const result=await inspect(await context.newPage(),entry);
        console.log(entry.id,result.status,'outbound_count',result.outbound);
      }finally{await context.close()}
    }
  }finally{await browser.close()}
  console.log('공개 링크 확인만 수행했습니다. 검색 색인·순위·실제 트래픽 효과를 뜻하지 않습니다.');
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main(process.argv.slice(2)).catch(err=>{console.error('중단:',err.message);process.exitCode=1})
}
