# 2026-10-27 링크위키 등록 작업 복원

사용자가 제공한 작업 화면 캡처에 근거하며, 구글 색인이나 공개 백링크 확보와는 구분합니다.

| 등록처 | 확인한 상태 | 근거 |
|---|---|---|
| Anoox | 제출 진행 확인; 공개 링크 미확인 | 10:02~10:07 제출 화면, 기존 기록 |
| Viesearch | 무료 등록 심사 대기 | 09:19 Wait in Line 이후 미리보기 화면 |
| ExactSeek | Addition Pending | 13:30 회원 Free Listings의 LinkWiki 행 |
| FreeWebSubmission | 일괄 처리 완료 화면 | 13:16 실행 결과, 대상 linkwiki.info |
| Portelo | 시스템 전송 성공 | FWS 결과 Connected Success |
| SearchThis | 시스템 전송 성공 | FWS 결과 Connected Success |
| SecretSELabs | 시스템 전송 성공 | FWS 결과 Connected Success |
| SitesOnDisplay | 시스템 전송 성공 | FWS 결과 Connected Success |
| SonicRun | 시스템 전송 성공 | FWS 결과 Connected Success |
| Archive | 클릭 완료 필요 | FWS 결과 Click to Complete |
| Amidalla | 실패 | FWS 결과 502 Bad Gateway |
| Sites Internationaux | 최종 상태 미확인 | 입력 양식 화면까지만 확인 |
| Submit.biz | 최종 상태 미확인 | 입력 양식 화면까지만 확인 |

ExactSeek도 FWS 일괄 결과에는 Success로 표시되지만, 이후 회원 페이지에는 Addition Pending으로 표시돼 최종 상태를 `pending_review`로 기록했습니다.

이전에 대화로 보고된 ChipJourney 심사 대기와 Curlie 503 실패는 개별 제출 URL이 확정되지 않아 CSV에 추정 URL을 넣지 않았습니다. 나중에 정확한 URL을 확보하면 추가하세요.

`seo/backlink_manager.py import --file seo/backlinks-recovered-20261027.csv`를 실행하면 기존 Anoox 기록을 중복 추가하지 않고 상태를 통합합니다. 모든 `public_url`은 확인 전이라 비워둡니다.
