# 2026-11-14 세션 접근 확인

## GitHub
- Codex GitHub 연결에서 `a01088293068-ui/link` 저장소를 조회했습니다.
- 연결 계정의 저장소 권한은 admin/maintain/push를 포함합니다.
- `main` 기준 최신 커밋은 `78b23bac0266f5cde97d3c7ce55ea2cc9817f167` (`Track three confirmed directory submissions`)입니다.
- 기본 브랜치와 파일 조회 도구는 동작합니다. 현재 API에서 GitHub Actions secret/variable 값을 읽는 도구는 제공되지 않습니다.

## Google Search Console
- 현재 연결 도구 목록에 Search Console API(사이트 목록, Search Analytics, URL Inspection) 호출 도구가 없습니다.
- `sc-domain.info`는 속성 식별자가 아닙니다. 기존 workflow 기본 속성 표기는 `sc-domain:linkwiki.info`이며, GSC 보고에는 해당 property에 대한 서비스 계정 `GOOGLE_SERVICE_ACCOUNT_JSON` 비밀값이 필요합니다.
- 저장소 문서 `SEARCH-CONSOLE-MONITOR-SETUP.md`는 secret을 설정하고 수동 실행해 비공개 artifact에서 결과를 확인하도록 설명합니다. 이 세션은 secret 읽기/Actions workflow 실행 도구를 노출하지 않아 API 수집을 호출할 수 없습니다.

## 공개 사이트 라이브 점검
- `/robots.txt`: HTTP 200, 전체 크롤 허용 및 `sitemap.xml`, `sitemap-v2.xml` 지정.
- `/sitemap.xml`, `/sitemap-v2.xml`: HTTP 200. `/directory` canonical URL이 사이트맵에 포함됨.
- `/directory`: HTTP 200, `<title>사이트모음 전체 목록 | 228개 사이트 검색·비교 - 링크위키</title>`, H1 `주소모음·링크모음·사이트모음 통합 검색`, canonical `https://linkwiki.info/directory`, robots `index,follow`, 검색엔진이 읽을 수 있는 HTML에 228개 목록 항목이 렌더링됨.
- `/directory.html`은 `/directory`로 200 redirect/canonicalized됩니다.
- 이 세션에서 새 색인 요청은 보내지 않았고 Google 색인 상태·검색 순위 변화도 관측하지 않았습니다.

## 다음 단계
Google 연결 앱 도구나 GitHub Actions workflow dispatch 및 artifact 조회 도구에서 GSC API 권한을 노출하면, `sc-domain:linkwiki.info`로 검색 성과·URL Inspection 보고서를 읽을 수 있습니다. GitHub Actions workflow dispatch는 현재 제공된 도구 목록에 없습니다.
