# 링크위키 211개 사이트 연결 상태 — 실측 후속 점검 (2026-11-10)

## 원천 증거 및 주의

- 자동 검사: https://github.com/a01088293068-ui/link/actions/runs/42759570917
- 아티팩트: `linkwiki-directory-reachability` 내 `directory-reachability.json`
- 2026-11-10 05:03 UTC 기준, 공개 목록 211개 URL을 읽기 전용 HTTP 요청으로 조사함.
- 200 OK: **172개**. 접근 제한(HTTP 403/429 등): **24개**. 추가 검토(리디렉션·특수 HTTP): **8개**. 연결 미확인(네트워크 오류 등): **7개**.
- 이 검사는 사이트의 공식 소유권, 상업적 조건, 안전성이나 Google 색인 여부를 보증하지 않음. **403/429, 타임아웃은 사이트 폐쇄의 증거가 아님.**

## 검증된 공식 HTTPS 목적지 4개 반영

자동 검사에서 기존 등록 주소가 다른 HTTPS 도메인으로 이동한 것을 확인했고, 변경 대상의 새 도메인을 별도 공개 페이지로 재조회함.

| 사이트 | 기존 등록 URL | 현재 확인된 목적지 | 조치 |
|---|---|---|---|
| Microsoft Copilot | https://copilot.microsoft.com/ | https://copilot.com/ | 등록 정보와 정적 링크 수정 |
| NotebookLM | https://notebooklm.google.com/ | https://notebook.google.com/ | 등록 정보와 정적 링크 수정 |
| Runway | https://runwayml.com/ | https://runway.com/ | 등록 정보와 정적 링크 수정 |
| Plex | https://www.plex.tv/ | https://watch.plex.tv/ | 등록 정보와 정적 링크 수정 |

`assets/verified-directory.json`, `assets/directory.js`, 전체 정적 사이트모음, AI·영상 카테고리를 동기화하고 회귀 테스트로 이전 링크 재유입을 방지함. 도메인 변경은 관련 콘텐츠의 편집이며 자체적으로 Google 순위 개선 증거는 아님.

## 남은 4개의 리디렉션/특이 응답

| 사이트 | 관찰 | 조치 원칙 |
|---|---|---|
| 대한상공회의소 코참넷 | HTTPS에서 HTTP 내 경로로 이동됨 | HTTPS가 유지되는 공식 URL을 확인할 때까지 자동 변경 금지 |
| 네이버 스포츠 | `sports.naver.com`에서 `m.sports.naver.com`로 이동 | 반응형·모바일 전환 가능. 현재 등록 공식 출발 주소 유지 |
| KLPGA | `www.klpga.co.kr`에서 `klpga.co.kr/web/main/index`로 이동 | 공식 도메인 변경 여부 확인 후 수정 검토 |
| 에펨코리아 | HTTP 430 특이 응답 | 차단·서버 정책 여부 불확실. 일시 상태로 폐쇄 판정 금지 |

## 자동 요청에서 연결을 확인하지 못한 7개

건강보험심사평가원, 한국소비자원, SLR, MBC, (미국)뉴욕코리아, (터키)튀르키예 한인회, (싱가포르)코닷싱.

자동 검사상 네트워크 오류/연결 실패였으며 실제 서비스 종료 또는 도메인 상실 확인은 아님. 공식 출처나 브라우저에서 추가 확인이 이루어지기 전까지 목록에서 임의 삭제하지 않음.

## 접근 제한 24개

Brave Search, Ecosia, 오늘의유머, 퀘이사존, 비마이펫, 오늘의집, 다이닝코드, 뽐뿌, 아카라이브, 레딧, Claude, Perplexity, Canva, Gamma, QuillBot, Leonardo AI, Sofascore, ATP Tour, 웹툰가이드, (영국)영국사랑, (말레이시아)코리안프레스, (인도)인도웹, (전세계)코리안넷, (미국)에스디사람.

HTTP 403·429는 특히 봇 차단·요청량 제한과 양립할 수 있어 품질 불량이나 폐쇄 사이트로 표시하지 않음.

## 검색 노출과 연결되는 작업 원칙

1. 핵심 `/directory`가 Google에 미색인인 원인을 이 검사만으로 설명할 수 없음. 페이지는 공개 HTTP 및 SEO QA에서 정상 확인됨.
2. 변경된 4개 사이트가 디렉터리·카테고리 검색과 같은 데이터로 렌더링되도록 검증함.
3. 실제 외부 링크 오류를 줄이는 것은 이용자 가치를 높이지만 상위 순위 상승을 보장하지 않음.
4. 다른 사이트의 차단 정책을 우회하거나 대량 재요청하지 않음. 공식 주소에 대한 추가 증거가 있을 때만 데이터 변경.
