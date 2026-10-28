# 백링크 신규 제출 자동화: 2026-10-28

## 실제 API 발견 및 연결

Viesearch 공식 문서에 `POST https://viesearch.com/api/submit` 엔드포인트, `x-api-key` 인증 및 30초당 1회 제한이 명시되어 있습니다. 이 API는 새 자원을 **심사 대기열에 제출**합니다. 등록 승인/검색 노출은 보장하지 않습니다.

공식 문서: https://viesearch.com/api/post-submit

`seo/backlink_viesearch.py`는 위 API의 실제 호출을 지원합니다. 기본 실행은 키가 없어도 동작하는 dry-run입니다.

```bash
cd ~/Downloads/linkwiki-seo-deploy
python3 seo/backlink_viesearch.py
```

다만 **LinkWiki의 Viesearch 신청은 2026-10-27 이미 심사 대기 상태**이므로, 기존 장부를 읽고 자동 제출을 건너뛰도록 했습니다. 재신청을 반복하지 마세요.

나중에 별도 사이트를 정당하게 제출할 때에만 Viesearch 계정 설정의 API 키를 등록하고 `--url`을 지정하여 `--execute`로 한 번 제출할 수 있습니다. 같은 등록처에 같은 웹사이트를 중복 신청하지 않도록 장부를 먼저 확인해야 합니다.

## 신규 후보 일괄 관리

`seo/backlink-candidates-20261028.csv`에 신규 후보 8곳을 담았습니다. 각 플랫폼의 **자체 안내 페이지**를 확인했지만 실제 등재·SEO 효과를 검증한 것은 아닙니다. 플랫폼별 로그인·심사와 API 자동 제출 허용 여부는 구분해야 합니다.

```bash
python3 seo/backlink_manager.py import --file seo/backlink-candidates-20261028.csv
python3 seo/backlink_manager.py report
python3 seo/backlink_manager.py list
```

이를 통해 기존 등록처와 신규 후보를 중복 없이 하나의 장부에서 관리합니다.

## 중요한 한계

- 위 8개 신규 후보는 **자동 제출 완료가 아닙니다.**
- 현재 공식 제출 API가 확인된 플랫폼은 Viesearch 1곳이며, 여기도 이미 등록 대기 상태입니다.
- 다른 플랫폼 등록 폼에 CAPTCHA·로그인·이메일 인증이 있으면 무단 우회하지 않습니다.
- 운영 결과가 `submitted`라도 반드시 공개 URL에서 `linkwiki.info` 링크를 확인해야 합니다.
- 특정 도메인의 검색 순위를 올리기 위한 무분별한 등록을 권장하지 않습니다.
