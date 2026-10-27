# 링크위키 백링크 자동 검증·관리

기존 `seo/auto_seo.py`, `build.py`, 블로그 자동 게시, Cloudflare Pages 설정은 변경하지 않습니다.

## 이 모듈이 실제로 하는 일

- 기존 외부 제출 기록을 CSV에서 한 번에 가져오기
- 등록처 중복 감지 (동일 플랫폼+제출 URL)
- 실제 공개 URL의 HTML에서 `linkwiki.info` 링크 존재 여부 검사
- `nofollow`/`ugc`/`sponsored`, 메타 robots `noindex`, HTTP 오류 분리
- 최대 30개씩 매주 자동 재검사하고 Markdown 보고서/JSON 장부를 GitHub에 보관
- GitHub Actions에서 매주 일요일 한국시간 10:42 검사 + 수동 실행 가능

## 현재 자동화되지 않는 것

- 임의의 외부 디렉터리에 가입하거나 등록 폼을 무차별 제출하는 기능
- CAPTCHA, 이메일 본인 확인, 운영자 심사 우회
- 각 사이트의 API 약관과 인증 정보가 확인되지 않은 상태에서 자동 제출
- Google 색인·검색 순위 상승의 보장

등록처 제출을 자동화하려면 사이트별로 공식 API나 자동 제출 허용 방식이 확인되어야 합니다. 이 정보가 없는 등록처는 장부에 기록하고 공개 URL을 검증합니다. 자동 제출 성공으로 표시하지 않습니다.

## Mac 실행 명령

```bash
cd ~/Downloads/linkwiki-seo-deploy
python3 -B -m unittest discover -s tests -p 'test_backlink_manager.py' -v
python3 seo/backlink_manager.py import --file seo/backlinks-import-template.csv
python3 seo/backlink_manager.py report
python3 seo/backlink_manager.py list
```

이미 제출한 등록처를 CSV에 추가할 때 반드시 실제 상태를 기록합니다.

| 필드 | 의미 |
|---|---|
| platform | 사이트명 |
| submission_url | 신청하거나 제출한 주소 |
| public_url | 공개 등재 URL; 모르면 빈칸 |
| submission_status | not_submitted, submitted, pending_review, approved, rejected, unknown |
| notes | 비고 |

공개 URL이 채워져 있다면 다음 명령으로 링크를 검사합니다.

```bash
python3 seo/backlink_manager.py audit --limit 30
```

결과는 `seo/backlink-registry.json`과 `seo/backlink-status.md`에 저장됩니다.

## GitHub 연결

이 소스의 `.github/workflows/backlink-audit.yml`이 GitHub에 게시되면 자동 검사 일정이 등록됩니다. 기존 콘텐츠 발행 워크플로와 별개입니다. 공개 URL이 없는 제출 기록은 검증하지 않고 `unverified`로 남깁니다.

자동 검사 결과에서 `verified_link`는 공개 HTML에 링크가 발견됐다는 뜻이며, 백링크의 검색엔진 가치나 인덱싱을 뜻하지 않습니다.

## 기존 제출 내역 통합

첨부된 예시 CSV에는 대화에서 확인된 Anoox 제출 확인 URL을 *제출 상태*로만 넣었습니다. 이를 공개 백링크 URL로 간주하지 않습니다. Curlie(기술적 실패)와 ChipJourney(심사 대기)는 정확한 제출 URL이 확인되면 추가할 수 있습니다.
