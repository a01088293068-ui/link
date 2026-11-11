# 링크위키 2026-11-11 추가 백링크 등록 후보 검토

대상 https://linkwiki.info/ . 기존 Dreamboat, SYDE는 중복 제출 금지.
Disquiet 자동화 Chrome에서 사람 인증 실패, 재시도 자동화 제외.
현 단계의 아래 6곳은 **후보**이며 추가 제출 0건, 승인 0건.

| 등록처 | 직접 확인된 공개 URL | 공개 양식·조건 | 현재 판단 |
|---|---|---|---|
| Joinly | https://joinly.xyz/submit-startup | 웹사이트 URL, 이메일(비공개 안내), 한 줄 설명, 소개, 국가, 필수 대표 이미지, 약관 동의 | 가입 없이 양식 노출; 개인정보 제공 및 이미지 첨부 필요. 무인 제출 금지 |
| LaunchPedia | https://launchpedia.co/submit/ | Name, Email, Product Name, Website Link, Affiliate link 필드 | 계정 확인 전에는 담당자 이메일·이름 요구; 개인정보 범위 확인 필요 |
| Phyco | https://phyco.org/submit | URL, 이메일 비공개, 60단어 이상 설명, 이미지 및 스크린샷, 가격·플랫폼 필드, 편집 검수 | 폼 존재, 계정 없이 접근 가능하나 실제 제출 전 이미지 등 준비 필요 |
| Startup Collections | https://startupcollections.com/submit-product/ | 공개 Submit Product 폼, Google iframe, Resource name, Website URL, Description, Your name/email, bot check | 제3자 iframe 및 봇 확인 요소 확인. 자동화 재시도 대상 아님 |
| Startup Stash | https://startupstash.com/add-listing/ | Typeform 임베드 기반 상품 등록 폼 | 서드파티 양식 정책/필드 및 실제 무료 여부 추가 확인 |
| SoMuch | https://www.somuch.com/submit-links/ | 무료 심사 가능, 이메일 확인 3일 안에 해야 함, 사이트 전체 URL 필요. 성인/리디렉션/광고만 있는 사이트 제외 | 링크위키가 정책에 적합한지 재검토; 미제출 |

출처(각 공식 등록 화면): 위 표의 URL에서 2026-11-11 조사.

자동화 코드 `tools/outreach-batch.mjs`에서 `scan` 명령으로
한 번에 6개 공개 폼 접근성을 점검할 수 있게 했습니다.
로컬 컴퓨터의 개인정보를 저장소에 수집하지 않습니다.
브라우저 진단은 제출이나 자동 회원가입이 아니며, VPN 확인 후 실행합니다.

유의:
- 등록 여부, 승인 여부, 공개 백링크 실재 여부는 각각 별도 상태.
- 이미 제출한 사이트에 재제출하지 않음.
- 단순 링크 등록을 위해 실제 사용하지 않는 사람 이름·주소·이메일을 조작하지 않음.
- 검색 순위 개선/Google 링크 평가를 주장하지 않음.
