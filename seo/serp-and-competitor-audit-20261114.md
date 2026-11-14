# 한국 Google 현재 SERP·경쟁사 및 기술 SEO 점검 — 2026-11-14

## 검색 결과 스냅샷
현재 공개 웹 검색 도구에서 각 질의 최대 10개 결과를 확인했다. 이 결과는 한국 Google 표본과 동일하지 않을 수 있고, 위치·개인화·검색 시점 영향을 받으므로 순위 지표로 사용하지 않는다.

### 주소모음
관측된 결과: jusonara3.com, pinksmoky.com, hoppang.net, mannaholic.com, ygy00.com, YouTube, Spreaker, jjongi.com, moel.go.kr, gall.dcinside.com.

### 링크모음
관측된 결과: juso3.net, linkmoeum.org, hoppang.net, jusoworld.com, 꿀주소 IDN domain, smart-marketing.pro, pinksmoky.com, linkdamoa.com, 주소온길 IDN domain, flashbannernow.com.

### 사이트모음
관측된 결과: 주소핫 IDN domain, hoppang.net, jusonara3.com, YouTube, Spreaker, archive-me.net, nayayo.com, dkexpress.co.kr, dailymotion.com. 다른 query top-10 에서는 핑스모·주소콜 등 추가 노출도 관측됨.

20개 도메인 제출 목표는 각 키워드 상위 20 결과의 전수 증거를 수집할 수 있는 SERP 데이터 도구가 제공되지 않아 충족하지 못했다. 위는 실제 검색 결과에서 관측한 후보이며 전체 20위 결과라고 확대 해석하지 않는다.

## 읽은 경쟁사 페이지의 차이점
- **핑스모**: 매거진형 편집, 목적·상황별 4개 섹션, 20개 상세 페이지, 이용 안내와 질문. 강한 내러티브/정보 구조. 크롤된 본문에서 인증·갱신 주장 등은 운영자의 자기 보고이며 독립 검증이 아님.
- **주소핫**: 본문 텍스트, FAQ 및 분야별 내부 랜딩이 풍부하고 head terms를 직접 사용. 본문은 최신주소/우회 도메인 안내 방향과 성인·도박 연계 주소가 섞여 품질·정책 적합 리스크가 있음. 링크위키는 공식 일반 서비스 탐색에 차별점을 둔다.
- **주소나라(jusonara3.com)**: 카테고리 페이지가 세분됐으나 adult, casino, torrent 등과 제휴 추적 URL이 다수 노출됨. 같은 형태로 복제하지 않음.
- **주소핀(jusopin.com), 여기여(nayayo.com), 주소봇(jusobot.net)**: 출처 설명·최근 변경 기록·운영 기관/공식 도메인 안내와 접속 점검을 전면에 제시. 링크위키가 추격할 정보 효용 기회는 개별 항목의 검증 출처, 변경 이력, 실제 확인일을 기록하는 구조이나 근거 없이 배지/점검일을 주장하면 안 됨.
- **MoaKit / 사이트모음류**: 대규모 분류와 실제 사용 가이드가 보인다. 단순 수량 확장보다 목록의 정확한 구분과 탐색 사용성을 개선하는 편이 차별화에 맞음.

실제 페이지 콘텐츠/메타데이터에 접근했던 경쟁사: jusonara3.com, pinksmoky.com, hoppang.net, mannaholic.com, ygy00.com, juso3.net, linkmoeum.org, jusoworld.com, 주소핫 IDN domain. 전체 20개 상위 페이지의 backlink·indexed page count는 확보할 수 없었다. 그런 수치를 꾸며내지 않는다.

## LinkWiki 라이브 기술 상태 (2026-11-14)
- `robots.txt`: HTTP 200, `Allow: /`, 두 sitemap 파일 선언.
- `sitemap.xml`/`sitemap-v2.xml`: HTTP 200, 동일 XML. extensionless canonical URLs를 사용하며 `/directory` 포함.
- `/directory`: HTTP 200, self canonical, `index,follow`, H1 `주소모음·링크모음·사이트모음 통합 검색`, 서버 렌더링 목록 228개. query URL은 directory search UX에 쓰이며 sitemap에는 query variant가 포함되지 않음.
- Homepage: title `주소모음 | 228개 사이트 검색, 분야별 링크모음·사이트모음 - 링크위키`, description과 H1은 직접 이름 검색 및 카테고리 탐색을 함께 표현. WebSite JSON-LD 존재.
- 기존 internal-link 감사(11/10 보고서)에서 `/directory`로 링크되는 서로 다른 내부 문서 32개였음. 현재 라이브 homepage에도 directory, category, guide, topical article 링크가 다수 있음.
- CSS/JS 기반 인터랙션이 있으나 실제 목록과 기본 콘텐츠는 HTML에 렌더링되어 검색봇이 JavaScript 없이도 읽을 수 있음.
- 저장소의 `.github/workflows/search-console-monitor.yml`은 읽기 전용 GSC 측정용이며, 현재 workflow dispatch 도구/API 인증이 없어 새 실행을 시도할 수 없음.

## 가용 GSC 기준선 (변경 전후 아님)
2026-11-10 저장 보고서에서 확인된 데이터 종료일 2026-11-07: `주소모음` 1 imp/1 click/111.0, `링크모음` 4/1/123.0, `사이트모음` 공개 행 미관측. `/directory` URL Inspection: 2026-11-08 crawled - currently not indexed, fetch successful, canonical self. 이 정보는 최신 7/28/3개월 성과가 아님.

## 백링크 후보 조사 현황
당일에는 후보 검토를 추가 진행했으나 제출/공개 링크 생성은 하지 않았다.
- **saaskorea.com**: 국내 SaaS 백과사전, 현재 316개 서비스 공개. 검색 결과에서 LinkWiki listing 또는 공개 submit form을 확인하지 못함. 웹 디렉터리 유형에 직접 적합해 보이지만 LinkWiki는 SaaS가 아니므로 eligibility와 등록 경로 검증 필요. 이번에는 제출하지 않음.
- saaskr, Dreamboat, OpenWebSide: 기존 LinkWiki 등록/공개 페이지가 저장소에 기록돼 있으므로 중복 제출 금지.
- Daum 검색등록: 기존 검색 등록 결과가 있으나 독립 소개 링크와 분리.
- 게시판·커뮤니티에서 단순 홍보성 글을 만들거나 등록을 대량 자동화하지 않음.

## 다음 데이터 수집/실행의 선행 조건
- 정확한 7일/28일/3개월 GSC 비교 및 indexed status 최신화: 현재 세션에서 Google Search Console readonly API 도구 또는 GitHub Actions workflow dispatch + artifact 조회 도구가 없음.
- 현재 저장소 파일 조회/PR/브랜치 권한은 있으나 Actions REST dispatch는 익명 HTTP 401. Google secret은 조회 대상이 아니며 비밀값을 요청하지 않음.
- 최소 50개 후보 전수 검증에는 검색 결과별 등록 양식/운영 상태/비용/공개 링크를 읽을 수 있는 후보 데이터 수집이 더 필요. 후보 숫자만 채우지 않음.
