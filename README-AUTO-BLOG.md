# LinkWiki SEO 자동 게시판 통합

이 패키지는 기존 SEO 정적 홈페이지의 HTML, CSS, 이미지, 가이드, CTA를 보존하고 최신 이용 가이드 섹션과 `/blog/`를 추가합니다.

## GitHub 저장소

기존 `a01088293068-ui/link` 저장소에 **ZIP 안의 파일과 폴더를 루트에 업로드**하세요. 기존 원고 `content/post_20261026_144625.md`는 품질 검토 후 `content/address-directory-safety-guide.md`로 교체했습니다. 원고 중복 게시를 막으려면 **이전 원고 파일 하나만 삭제**하세요. 다른 글이 있다면 유지하세요. 새로운 글을 `content/*.md`로 올리면 다시 빌드됩니다.

## Cloudflare Pages 설정

- Git repository: `a01088293068-ui/link`
- Production branch: `main`
- Framework preset: `None`
- Root directory: 저장소 루트 (비워둠)
- Build command: `python3 build.py`
- Build output directory: `dist`

## 로컬 확인 (macOS)

```bash
cd ~/Downloads/LINKWIKI-SEO-INTEGRATED
python3 build.py
python3 -m http.server 8000 --directory dist
```

브라우저에서 `http://localhost:8000/`와 `http://localhost:8000/blog/`에 접속하세요.

## 주의

- Google Indexing API를 일반 블로그 글에 사용하지 않습니다.
- 검색 노출은 보장되지 않습니다. 사이트맵은 URL 발견을 돕는 수단입니다.
- 공개 기본 주소는 기존 `https://linkwiki.info/`를 유지합니다. Cloudflare 커스텀 도메인 연결 전에는 검색엔진 색인 대상 도메인 설정을 재확인하세요.
- 글 생성 프로그램 `auto_seo.py`는 별도로 실행하며, Github 업로드 경로는 `content/`입니다.
