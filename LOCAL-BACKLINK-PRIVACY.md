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
