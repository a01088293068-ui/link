# 링크위키 AI SEO 자동화 설치/운영 가이드

## 1. 무엇이 자동화되나

`seo/seed_keywords.txt`에 설정된 주제에서 하루에 하나의 시드를 순환합니다. Serper로 관련 검색어와 경쟁 결과 제목·요약을 조사하고 관련성 기반 후보를 선정합니다. GPT-4o가 정보를 작성하고 독립된 GPT-4o 검수 및 코드 검사를 통과하면 `content/`에 글 1개를 저장합니다. GitHub Actions가 해당 변경을 커밋하면 Cloudflare Pages가 배포합니다.

검색량, 경쟁 난도, 구글 검색 순위는 이 코드만으로 검증되지 않습니다. 유용한 콘텐츠가 항상 색인·상위노출되는 것은 아닙니다.

## 2. 준비: GitHub Secrets

GitHub `a01088293068-ui/link` → **Settings → Secrets and variables → Actions → Secrets**에서 아래 **Repository secrets** 2개를 만드세요.

- `OPENAI_API_KEY`: OpenAI API 키
- `SERPER_API_KEY`: Serper API 키

비밀 값은 코드, 채팅, 저장소 파일에 붙여넣지 마세요. 별도의 GitHub PAT는 Actions 내 콘텐츠 Commit에 필요하지 않습니다. GitHub Actions에는 `GITHUB_TOKEN`을 사용하도록 설정되어 있습니다.

## 3. 첫 시험: 게시하지 않고 실행

GitHub → **Actions → LinkWiki SEO research and publish → Run workflow** → `publish=false`를 선택하고 실행합니다. API 비용이 발생할 수 있으며, 통과한 원고가 있을 때만 실행 결과의 `seo-reviewed-draft` Artifacts에 저장됩니다. 중복이나 품질 미달이면 게시하지 않고 로그에 사유를 남깁니다.

## 4. 수동 게시 검증

테스트 결과가 적절하면 같은 워크플로를 `publish=true`로 1회 실행합니다. 글이 통과하면 `content/`와 `seo/history.json`이 Commit됩니다. Cloudflare Pages 빌드 상태와 `/blog/` 새 글 노출 여부를 검사하세요.

## 5. 정기 자동 실행 켜기

GitHub → **Settings → Secrets and variables → Actions → Variables** → `New repository variable`:

이름 `AUTO_SEO_ENABLED`, 값 `true`.

이때부터 GitHub Actions가 월·수·금 02:15 UTC(한국 시간 11:15)에 실행을 시도합니다. 플랫폼 사정에 따라 예약 시간이 지연되거나 실행이 건너뛰어질 수 있습니다. **품질 기준 통과 시에만 최대 1개 발행**합니다. 끄려면 같은 변수를 `false`로 바꾸세요.

## 6. GitHub Actions 쓰기 권한

자동 Commit에 `Resource not accessible by integration` 오류가 나오면 Settings → Actions → General → Workflow permissions에서 **Read and write permissions**를 확인하세요. 저장소나 조직 정책에 따라 변경이 막혀 있을 수 있습니다. 작업 파일을 로컬 PAT로 올릴 때 워크플로 수정 권한이 부족하면 GitHub 웹 편집기에서 `.github/workflows/auto-seo.yml`을 직접 생성해야 할 수 있습니다.

## 7. 운영 원칙

- 새 글의 내용은 검색 결과 스니펫에 있는 모든 사실을 검증한 것이 아닙니다. 중요한 정보를 단정하는 글은 별도 확인 후 게시합니다.
- 중복 감지, 글 길이, 키워드 관련성, 독립 AI 검수를 통과하지 못하면 글은 올라가지 않습니다.
- `AUTO_SEO_ENABLED`를 활성화하기 전에 첫 실제 글과 검색 노출 상태를 확인하세요.
- 일반 블로그 글에는 Google Indexing API를 쓰지 않습니다.
- 구글봇에게만 다른 콘텐츠를 보여주는 클로킹이나 가짜 클릭·백링크 게시 기능은 포함하지 않습니다.
- Search Console 실적 기반 자동 개선은 추후 별도 연결해야 합니다.

## 로컬 시험

```bash
cd ~/Downloads/linkwiki-seo-deploy
python3 -B -m unittest discover -s tests -v
```

로컬에서 API 키가 준비된 경우:

```bash
python3 seo/auto_seo.py
```

이 명령은 검수 후 `seo/drafts/`에만 초안을 만듭니다. 실제 게시가 필요할 때만 `--publish`를 추가하세요.
