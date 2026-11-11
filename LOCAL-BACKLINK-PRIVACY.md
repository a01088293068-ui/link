# 링크위키 무료 로컬 백링크 도구 — 개인정보 보호 기본값

## 보호 범위 (중요)

이 도구는 백링크 등록을 위해 맥북의 Chrome을 **별도 프로필**로 실행합니다.
기존 리쑤화 Google 프로필을 복사하거나 비밀번호·쿠키·접속 IP를 수집하거나 GitHub에 게시하지 않습니다.

하지만 **VPN 없이 접속하면 등록처는 인터넷 회선의 실제 공인 IP를 볼 수 있습니다.**
VPN에 연결해도 서비스 로그인(Google OAuth), 브라우저 식별 정보, 사이트의 서버 로그까지
익명화되는 것은 아닙니다. 링크위키 운영자임을 드러내는 등록 행위 자체도 남습니다.
완전한 익명성·Google 제재 없음·사이트별 정책 수락을 보장하지 않습니다.

- 브라우저 프로필: `.local-backlink-profile/` (로컬, Git 제외)
- 검증 이력: `.local-backlink-state/results.json` (로컬, Git 제외)
- 저장 항목: 외부 페이지 URL, 공개 링크 수, rel/noindex, HTTP 상태만 저장
- 저장 금지: 리쑤화 이메일, 실명, 비밀번호, 인증 코드, 쿠키, IP, 시스템 사용자명
- 외부 사이트는 접속 시 IP와 브라우저 정보를 볼 수 있고 Google 로그인은 계정 정보가 공유될 수 있음
- 중복 회원가입, CAPTCHA 우회, 탐지 회피, 자동 폼 제출 없음
- **기본 모드:** 명령 `list`, `privacy`는 인터넷 접속 없음
- 외부 접속은 반드시 `--privacy-confirmed --vpn-interface utunN` 필요.
- macOS에서 IPv4 및 IPv6 대상 경로가 모두 지정된 VPN 터널을 사용하는지 확인하지 못하면 실행 차단.
- 이 검사는 전체 DNS·IPv6·WebRTC 누출 방지를 보증하지 않음. VPN 앱의 킬 스위치·DNS 누출 방지·IPv6 누출 방지 기능을 활성화하고 테스트해야 함.
- 분할 터널 설정은 VPN을 우회한 직접 연결을 허용할 수 있으므로 사용하지 않음.

## 맥북에서 한 번 설치

기존 프로젝트 경로를 유지합니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
git pull --ff-only origin main
npm install
npx playwright install chromium
npm run outreach:test
```

Chrome이 설치돼 있어야 합니다. 기본 브라우저가 Chrome이 아니라면 공식
Chrome 설치가 필요합니다. 설치 자체는 외부 백링크 제출을 진행하지 않습니다.

## 인터넷 접속 전에 본인이 확인할 사항

1. Chrome에서 로그인한 **리쑤화 계정을 외부 등록처에 공개해도 되는지** 확인. 계정과 게시물은 연결될 수 있습니다.
2. IP 노출을 줄이려면 본인이 신뢰하는 VPN을 켜고 *공인 IP가 변경됐는지* 브라우저에서 확인.
   VPN의 접속 국가가 바뀌면 사이트의 추가 인증이 나올 수 있음. VPN 자체도 로그 정책을 확인.
   경로 검증은 VPN 보안의 전부가 아니며, DNS·IPv6·WebRTC 누출 테스트와 킬 스위치 설정이 필요합니다.
3. 등록처가 계정 닉네임·이메일을 공개하지 않는지 확인.
4. 데이터가 GitHub에 올라가지 않게 `git status --short --ignored`를 확인.
5. 등록 사이트의 자동화 정책을 확인. 로그인한 Google 계정은 별도 프로필에 1회 로그인.

## 명령

```bash
cd ~/Downloads/linkwiki-seo-deploy
npm run outreach -- privacy
npm run outreach -- list
# 인터넷 접속 없이 맥북의 VPN 터널 경로 확인
route -n get -inet 1.1.1.1 | grep interface
route -n get -inet6 2606:4700:4700::1111 | grep interface

# 두 결과 모두 같은 VPN 터널을 가리킬 때만 실행 (utun4는 예시)
npm run outreach -- open dreamboat --privacy-confirmed --vpn-interface utun4
```

`open`은 브라우저를 열어 로그인/등록 화면과 링크위키 소개 문구를 보여줍니다.
**회원가입·로그인·폼 제출을 자동 클릭하지 않습니다.** 기존 계정 중복 오류가 발생하면
추가 계정을 만들거나 동일 폼을 반복 제출하지 마세요.

다른 후보: `syde`, `disquiet`, `itjeom`. 각 사이트에서 실제 등록 방법·적합성을 확인하세요.

등록 완료 후 **외부의 공개 상세 페이지 URL**만 확보한 경우에 한해 다음 명령으로 검사할 수 있습니다.
쿼리 문자열(`?token=...`) 및 해시(`#...`)가 포함된 URL은 저장 전에 거부합니다.

```bash
npm run outreach -- verify https://example.com/public/linkwiki --privacy-confirmed --vpn-interface utun4
```

실제로 공개된 백링크가 없는 경우에는 `verify`를 실행하지 않습니다.
검사는 공개 페이지에 접속하기 때문에 등록처는 조회 IP를 볼 수 있습니다.
검증 결과에는 Google 검색 순위나 인덱싱에 대한 추정이 포함되지 않습니다.

## 계정 보호 및 삭제

`npm run outreach -- open ...`에서 Chrome 로그인 세션을 저장했다면
다음 명령으로 **해당 자동화 전용 로컬 프로필과 검사 기록만** 삭제할 수 있습니다.
**기존 Chrome의 리쑤화 프로필은 삭제하지 않습니다.** 삭제 전 백업 필요 여부를 확인하세요.

```bash
cd ~/Downloads/linkwiki-seo-deploy
rm -rf .local-backlink-profile .local-backlink-state
```

이 명령은 맥북 로컬의 데이터를 삭제할 뿐 등록 사이트나 Google 서버의 기존 기록을 지우지 않습니다.

## 여러 등록처 일괄 검토 (2026-11-11)

한 번의 명령으로 **기존 제출/승인된 Dreamboat·SYDE를 건너뛰고** 남은 한국어 등록처를 차례로 확인합니다.
등록 폼에 정확한 레이블이 붙어 있고 개인정보와 혼동되지 않을 때 프로젝트명·설명·공식 URL을 채웁니다.
그 외 필드, 계정 연결, CAPTCHA, 도메인 DNS 검증, 실제 게시 버튼은 임의로 처리하지 않습니다.
특히 Disquiet은 별도 인증·검토 절차이고 ITJEOM은 도메인 소유 검증이 필요합니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
git pull --ff-only origin main
npm install
npm run outreach:test
npm run outreach:batch -- plan
npm run outreach:batch -- run --privacy-confirmed --vpn-interface utun0
npm run outreach:batch -- status
```

- 현재 VPN 터널이 `utun0`인지 먼저 확인합니다. 바뀌었으면 실제 확인된 인터페이스로 바꾸세요.
- 실행 전에 VPN 앱의 킬 스위치, DNS 및 IPv6 누출 방지 설정을 켜야 합니다.
- `run`은 인터넷 접속을 수반하고 사이트별 `y` 입력을 받은 후 화면을 엽니다.
- 폼에 적절한 레이블이 없거나 로그인이 막히면 **자동으로 임의 제출하지 않습니다.**
- 검사/준비 상태만 `.local-backlink-state/outreach-queue.json`에 기록합니다.
  이 파일은 GitHub에 포함되지 않습니다. 공개 게시 URL이나 승인 증거로 혼동하지 마세요.
- **현재 제공 기능은 일괄 검토·일부 자동 입력이며, 로그인 우회나 모든 등록처에 대한 완전 자동 제출이 아닙니다.**
- Google 자동화 브라우저 로그인 제한이 재현될 수 있어, 기존 Chrome 로그인 세션을 무단으로 가져오지 않습니다.


## 2026-11-11: 새 등록처 6곳 일괄 *읽기 전용* 진단

연결된 계정이 차단된 Disquiet는 재시도하지 않으며, 기존 Dreamboat·SYDE도 재등록하지 않습니다.
신규 후보는 Joinly, LaunchPedia, Phyco, Startup Collections, Startup Stash, SoMuch입니다.
사이트별 정책에 따라 실명·이메일·이미지 또는 사람 인증이 필요할 수 있습니다.
이 등록처들이 LinkWiki를 최종 승인한다는 보장은 없습니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
git pull --ff-only origin main
npm install
npm run outreach:test
npm run outreach:batch -- plan
npm run outreach:batch -- scan --privacy-confirmed --vpn-interface utun0
npm run outreach:batch -- status
```

`scan`은 맥북에서 한 번에 6곳의 공개 등록 화면을 읽어 **폼 접근 가능성만 점검**합니다.
로그인·이메일·전화번호·CAPTCHA 입력, 폼 제출은 하지 않습니다.
페이지가 사람 인증을 요구할 경우 이를 우회하지 않고 별도 검토 상태로 남깁니다.
로컬 결과 파일에는 등록처 ID, 제한된 상태명, 날짜만 기록합니다.
공개 사이트에는 VPN 인터페이스를 통한 접속이 발생하므로, VPN의 킬 스위치와 누출 보호는 계속 필요합니다.

## 2026-11-11: 폼 3개 한 번에 준비

공개 등록 화면을 조사한 결과 Joinly, LaunchPedia, Phyco는 일반 폼이 확인됐습니다.
SoMuch는 사이트 정책상 LinkWiki의 콘텐츠 적합성이 검증되지 않아 자동 입력에서 제외했습니다.
Startup Collections/Startup Stash에는 봇 검사/외부 폼이 있으므로 제외합니다.

**이전 `scan`이 실행된 뒤** 다음 명령을 한 번 사용하면 세 사이트를 각각 별도 탭에
열어 **정확히 식별된 사이트 이름·설명·홈페이지 주소만** 자동으로 채웁니다.
사이트별 `y` 프롬프트가 없습니다. 인증·이메일·개인 주소·이미지·약관 동의·
제출은 자동으로 처리하지 않습니다. Google/사이트 정책에 따라 로그인이 차단될 수 있습니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
git pull --ff-only origin main
npm run outreach:test
npm run outreach:batch -- prepare --privacy-confirmed --vpn-interface utun0
```

브라우저가 떠 있는 동안 최종 제출은 사용자가 직접 내용을 검토한 뒤 해당 사이트에서
진행해야 하며, 이 도구는 등록 성공이라고 기록하지 않습니다.
모든 검토가 끝나면 터미널에서 Enter를 한 번 누르세요.

## 등록 시도 자동화 (2026-11-11)

사이트를 여는 것에 그치지 않고, **등록 제출 버튼까지 조건부로 한 번만 시도**하는 별도
`outreach:submit` 명령을 추가했습니다. 로컬의 Downloads/Desktop에서
파일 이름에 LinkWiki/링크위키 및 logo/로고가 들어 있는 유일한 이미지를 자동 탐색합니다.
후보가 여러 개이면 개인 사진이나 잘못된 배너가 업로드되지 않도록 자동 첨부하지 않습니다.

기존에 지정한 **리쑤화 이메일**은 개인 주소가 GitHub 파일에 남지 않도록 맥북 실행 시 환경변수로만 전달합니다.
프로그램은 이메일·사진 원본 파일명·쿠키를 CI 로그 또는 GitHub에 기록하지 않습니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
git pull --ff-only origin main
npm run outreach:test
LINKWIKI_OUTREACH_EMAIL='a01088293068@gmail.com' npm run outreach:submit -- --privacy-confirmed --vpn-interface utun0 --submit
```

실제 제출이 가능한 범위:
- LaunchPedia: 사이트의 Name/Email/Product Name/Website Link 등 필수 입력란을
  모두 안전하게 식별할 수 있고 인증/약관/추가 항목이 없으면 한 번 제출 시도
- Phyco: 이미지와 필요한 등록 항목을 확보하고 인증이 없을 때만 제출 시도
- Joinly: 제출 조항에 **마케팅 관련 개인정보 처리 동의**가 포함되어 있어
  사용자가 그 동의를 별도로 명시하지 않은 현재 상태에서는 자동 제출을 차단
- CAPTCHA·필수 체크박스·인증·미확인 개인정보는 자동 처리하지 않음
- 결과는 `.local-backlink-state/submission-attempts.json`에 저장.
  'submitted_unverified'는 등록 승인이 아닌 **제출 시도 후 확인 문구를 본 상태**입니다.

브라우저 실제 제출은 사용자 맥북에서만 수행됩니다. GitHub CI에서는 실제 외부
사이트 제출을 테스트하지 않으며, 정책 변경 및 CAPTCHA 때문에 0건 제출될 수도 있습니다.
VPN은 트래픽 안전을 완전히 보증하지 않으므로 킬 스위치, DNS/IPv6 누출 방지 확인이 필요합니다.

### 이름 필드도 포함한 단일 실행 예시

사용자 지정 리쑤화 연락 이메일과 표시 이름은 **맥북 프로세스에만 전달**합니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
git pull --ff-only origin main
npm run outreach:test
LINKWIKI_OUTREACH_EMAIL='a01088293068@gmail.com' LINKWIKI_CONTACT_NAME='리쑤화' npm run outreach:submit -- --privacy-confirmed --vpn-interface utun0 --submit
```

`--submit`은 실제 등록 버튼을 누르는 **시도**까지 포함합니다. 사이트가
인증·광고/마케팅 개인정보 동의·필수 이미지/카테고리·양식 변경을 요구하면
임의로 동의하거나 우회하지 않고 해당 사이트를 건너뜁니다. Joinly는 현재
결합된 마케팅 관련 개인정보 동의 때문에 자동 제출을 허용하지 않습니다.

## 제출 상태 오류 분석 — 2026-11-11

실행 로그: `joinly blocked_consent`, `launchpedia missing_fields`, `phyco missing_asset`.
세 곳 모두 신규 등록 성공이 아니며 **공개 백링크 0건**입니다.

개선된 `tools/outreach-submit.mjs`는:
- Downloads/Desktop의 링크위키 이미지 관련 하위 폴더까지 4단계 이내 탐색하며
  원본 이미지/개인 사진은 GitHub로 올리지 않습니다.
- LaunchPedia의 관련 입력란을 명시적 label, placeholder, name/id 순으로 찾고
  일치하는 필드가 여럿일 경우 안전하게 건너뜁니다.
- 찾지 못한 입력란의 **필드 키만** 터미널에 출력합니다.
- 사이트 측 인증·이메일·개인정보 동의·필수 이미지를 자동으로 위조하지 않습니다.
- 위 세 상태는 제출 실패/미실행 상태이므로 필요한 코드를 수정한 뒤 재진단이 가능합니다.
- 실제 Chrome 브라우저 기반 엔드투엔드 제출은 개발 환경에서 검증하지 않았습니다.

코드 테스트는 대체로 실제 폼 상호작용 테스트가 아니므로 `npm run outreach:test`
통과만으로 제출 성공을 주장할 수 없습니다.
