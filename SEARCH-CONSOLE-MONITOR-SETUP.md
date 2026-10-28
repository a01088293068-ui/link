# 링크위키 Search Console 자동 실적 분석

기존 SEO 자동 글 발행·백링크 모니터링·GitHub 배포 설정을 다시 하지 않습니다.

## 추가 기능

- 매일 한국시간 12:25에 지난 28일(최근 3일 제외)의 구글 검색어·페이지별 노출, 클릭, CTR, 평균 순위를 조회합니다.
- 결과는 GitHub Actions의 비공개 `search-console-performance` Artifact에 30일 보관합니다. 공개 저장소나 웹사이트에 업로드하지 않습니다.
- 읽기 전용입니다. 색인 강제 요청, CTR 조작, 외부 사이트 등록은 수행하지 않습니다.
- 인증 연결 전에는 이 기능만 실패하며 기존 글 발행·백링크 자동화에 영향이 없습니다.

## 최초 연결 한 번만

1. Google Cloud Console의 본인 프로젝트에서 **Search Console API**를 켭니다. 서비스 계정을 만들고 JSON 키를 발급합니다.
2. JSON 내 `client_email` 주소를 Search Console의 **linkwiki.info 속성 → 설정 → 사용자 및 권한**에 추가합니다.
3. GitHub `a01088293068-ui/link` → Settings → Secrets and variables → Actions → Repository secrets에서 `GOOGLE_SERVICE_ACCOUNT_JSON`이라는 이름으로 JSON 파일 내용 전체를 저장합니다. 채팅이나 저장소 파일에 키를 넣지 마세요.
4. 도메인 속성이 아닌 URL 접두어 속성만 등록된 경우, Repository variables에 `GSC_PROPERTY=https://linkwiki.info/`를 추가합니다. 도메인 속성일 때 기본값은 `sc-domain:linkwiki.info`입니다.
5. GitHub Actions의 `LinkWiki Search Console monitoring` → Run workflow로 한 번 실행합니다. 성공하면 해당 실행의 Artifacts에서 보고서를 확인합니다.
6. 확인 후 Repository variables에 `GSC_MONITOR_ENABLED=true`를 추가하면 정기 자동 수집이 켜집니다.

서비스 계정 키는 사용자만 관리합니다. 실제 인증을 아직 연결하지 않은 환경에서는 실측 결과를 확인할 수 없습니다.

## 로컬 기능 테스트

```bash
cd ~/Downloads/linkwiki-seo-deploy
python3 -B -m unittest discover -s tests -v
```
