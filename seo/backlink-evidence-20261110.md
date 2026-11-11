# 링크위키 외부 링크 증거 및 한국 중심 등록처 정리 — 2026-11-10

대상: https://linkwiki.info/ . 데이터 기준: 실제 공개 HTML을 검사한 GitHub Actions
[run 42772211393](https://github.com/a01088293068-ui/link/actions/runs/42772211393),
기존 접수 기록, 등록처 공개 설명. **새 외부 폼 제출은 이번 작업에서 0건.**
과거 공개 목록을 신규 제출로 계산하지 않는다.

## 1. 실제 HTTP HTML 앵커 검증: 고유 호스트 9개

| 출처 | 공개 근거 URL | HTTP HTML 검사 | 비고 |
|---|---|---|---|
| DevElif | https://develif.com/s/website-search-and-address-guides-by-linkwiki | direct href 2, no nofollow, no noindex | 기존 공개 |
| Ignlab Launch | https://launch.ignlab.net/t/linkwiki-2 | direct href 1, rel=nofollow ugc | 기존 공개 |
| OpenWebSide | https://openwebside.com/products/757213b7-1ce9-41ed-9eb2-6bae9af82688 | direct href 1, no nofollow, no noindex | 이전 pending_review 장부를 공개 상태로 복원 |
| saaskr | https://saaskr.com/saas/linkwiki-info | direct href 3, no nofollow | 기존 공개 |
| Sidedock | https://sidedock.io/products/%EB%A7%81%ED%81%AC%EC%9C%84%ED%82%A4linkwiki | direct href 1, no nofollow | 기존 공개 |
| Tistory | https://blacktetherscan.tistory.com/2 | direct href 1 | 운영자 작성 글; 독립 추천으로 계산하지 않음 |
| StartupAccelerator | https://startupaccelerator.dev/project/linkwiki | direct href 1, rel=nofollow | 기존 공개 |
| PHIndex | https://phindex.si/en/products/linkwiki.info | direct href 1 | 추적 파라미터 있는 링크; 기존 공개 |
| VibeLabs Lab | https://vibelabs.kr/lab/projects/238 | direct href 1 | 자가 작성 소개. 독립 추천으로 계산하지 않음 |

- OpenWebSide의 다른 이전 페이지
  https://openwebside.com/products/757213b7-1ce9-41ed-b0d7-a807df42adf7
  는 HTTP 200이지만 이번 정적 HTML 검사에서 직접 링크를 확인하지 못함. 같은 도메인인 만큼
  링크가 발견되더라도 신규 고유 출처 도메인은 아님.
- MeWebLink https://meweblink.com/website/linkwiki 는 이번 검사에서 HTTP 404, **확보로 미집계**.
- 9개 도메인이 linkwiki.info를 HTML로 연결한다는 사실은 확인되었지만
  Google 색인·링크 평가·검색 순위 개선은 확인되지 않았다.
- 링크 상태는 바뀔 수 있으므로 정기 재검증. 공개 URL 없는 제출은 여기에서 제외.

## 2. 승인 대기 (기존 접수, 중복 제출 금지)

- Launching Next: https://www.launchingnext.com/submit/ — 기존 접수번호 177330, 심사 대기.
  신청 영수증: https://www.launchingnext.com/thanks/?i=177330.
- Site Promotion Directory: https://www.sitepromotiondirectory.com/submit.php —
  이전 'Link submitted and awaiting approval' 확인. 일반 무료 심사가 수개월 걸릴 수 있음.
  실제 공개 URL 없음.
- GainWeb: https://gainweb.org/submit.php — 접수 대기.
- Viesearch, ExactSeek, LinkCentre, 그 밖의 과거 pending은
  seo/backlink-registry.json의 기록을 기준으로 중복 여부 먼저 확인.

## 3. 한국 독자 관련성이 높은 *새 등록 후보* (아직 미제출)

| 우선 | 후보 / 공식 등록 경로 | 지금 확인된 조건 | 상태와 다음 조치 |
|---|---|---|---|
| 1 | Dreamboat — https://dreamboat.kr/new | 국내 앱·웹서비스·사이트 소개; 무료; 이메일·Google 가입 필요 | 적합성 높음. 사용자 인증 세션 및 공개 프로필 필요. 현재 미제출 |
| 2 | SYDE 쇼케이스 — https://syde.kr/showcase | 국내 메이커 사이드프로젝트를 소개하는 쇼케이스. '내 프로젝트 등록하기' 표시 | 적합성 검토 후 계정으로 한 번만 등록. 현재 미제출 |
| 3 | Disquiet — https://disquiet.io/ | 메이커가 만든 프로덕트 소개 및 메이커로그 기능 | 공식 계정·프로덕트 등록 기능 확인 후 게시. 현재 미제출 |
| 4 | ITJEOM — https://web-directory.itjeom.com/ | 한국 웹 디렉터리. DNS TXT 소유 확인 후 1개 소개 페이지 발행 | 도메인 DNS 편집 필요. 인증 전 등록 미완료; 현재 미제출 |
| 5 | GeekNews — https://news.hada.io/ | 한국어 개발자·메이커 정보 공유. 발표 주제와 사용자 유용성이 있을 때만 | 관련 주제와 게시 규칙 확인 필요. 홍보성 링크만 올리지 않음; 미제출 |

**과거 제출 또는 정책 부적합 후보는 재신청하지 않음.**
OpenWebSide·Sidedock·saaskr·DevElif는 이미 공개.
Zearches는 duplicate_limit 재제출 거절 이력.
MeWebLink는 공개 링크 404, 정책 충돌 가능성.
247WebDirectory는 비영어 사이트 등록 제한, 01WebDirectory는 단순 외부 전송 사이트에 대한 제약이 있음.
유료·배지·맞교환 링크, 프로그램 대량 제출은 제외.

## 4. 제출용 자연어 소개

- 사이트명: 링크위키
- 대표 URL: https://linkwiki.info/
- 분류: 한국어 웹 디렉터리 / 사이트 탐색 및 주소 확인
- 짧은 소개:
  링크위키는 검색·포털, 커뮤니티, AI 도구, 스포츠, 영상, 웹툰 등 여러 분야의
  등록 사이트를 이름과 도메인으로 찾는 한국어 웹 디렉터리입니다.
  사이트별 이용 목적과 주소를 비교하고 공식 주소 확인 가이드를 참고할 수 있습니다.
- 정확성 유의: 사이트의 실시간 접속 가능 여부나 안전성·정식 운영을 보장하지 않음.

## 5. 실행 기준

1. 등록 전 사이트 정책·기존 목록·사용자 독자 적합성을 확인.
2. 로그인이나 도메인 소유 확인이 필요하면 권한을 가진 계정으로만 수행.
3. 접수 영수증과 승인·공개 링크를 분리하고, 공개 URL의 direct href/rel/noindex를 확인.
4. Google의 주소모음·링크모음·사이트모음 한국 검색 성과와 페이지 색인 상태를
   최소 일주일 단위로 실측. 링크를 만들었다는 사실만으로 순위 상승을 주장하지 않음.

## 2026-11-11 추가 확인: Dreamboat 실제 공개 등록

- 사용자 기존 계정에서 한 번 등록 완료: https://dreamboat.kr/u/linkwikiinfo/p/linkwiki
- 프로젝트명: 링크위키 (LinkWiki), 버전 v0.1, 업데이트 1건.
- 로그인하지 않은 외부 공개 렌더링에서 https://linkwiki.info/ 링크 추출 확인.
- 페이지 robots: `index, follow` 확인. 외부 링크 `rel` 값, Google 색인·순위 반영은 확인하지 못함.
- 공개된 자체 작성 소개글이므로 독립적인 제3자 추천으로 계산하지 않음.
- 장부: `seo/backlink-registry.json`에 Dreamboat 신규 1건 반영 (총 49건).
- 다음 후보 SYDE(https://syde.kr/showcase): 공개 쇼케이스와 '내 프로젝트 등록하기' 확인, 기존 등록 여부/정책/인증 검토 전에는 미제출.
- 로그인 계정의 이메일·개인 IP·맥북 식별자 및 Chrome 쿠키는 장부에 기록하지 않음.

## 2026-11-11 추가: SYDE 제출 및 Disquiet 최신 절차

- SYDE: 사용자 2026-11-11 제출 완료 보고. `seo/backlink-registry.json` 에 **제출됨**으로 기록.
  공개 상세 페이지 URL이 확인되지 않아 정식 외부 href 검증과 신규 확보 도메인 집계는 보류.
  재제출 금지. 공개 링크가 확인되면 그때만 검증 상태 갱신.
- Disquiet: https://disquiet.io/announcement 의 공식 리뉴얼 공지 확인.
  구글 OAuth 대신 Relate 계정 통합 후 **이메일 매직링크 로그인**으로 변경.
  본인 제작 제품만 등록 가능하며 `작성 → 검토 요청 → 승인` 절차를 거침.
  제품과 관계 없는 홍보글 반복 게시하지 말 것.
- 두 플랫폼 모두 기존 프로젝트 본 사이트 주소 대신 SEO 사이트인 https://linkwiki.info/ 만 소개.
- 실제 서비스 로그인 주소, 계정 이메일, IP, Mac 경로·세션 쿠키는 장부에 기록하지 않음.
