"""Grounded public explanation of directory edits and checking limitations."""
from datetime import date
from html import escape


def render(records, changes, categories):
    """Produce update disclosure from the real catalogue and dated edit ledger."""
    if not isinstance(records, list) or not records:
        raise ValueError("Directory maintenance requires a real, nonempty catalogue")
    edited = changes.get("/directory")
    try:
        date.fromisoformat(edited)
    except (TypeError, ValueError):
        raise ValueError("Directory maintenance requires a valid documented edit date")
    rows = []
    for category, slug, heading, _ in categories:
        count = sum(item.get("category") == category for item in records)
        if count < 1:
            raise ValueError("Missing category in directory: " + slug)
        change = changes.get("/categories/" + slug)
        if change:
            try:
                date.fromisoformat(change)
            except ValueError:
                raise ValueError("Invalid category update date: " + slug)
        rows.append(
            '<tr><th><a href="/categories/' + escape(slug) + '">' +
            escape(heading) + '</a></th><td>' + str(count) + '개</td><td>' +
            escape(change or "미기록") + '</td></tr>')
    return (
        '<div class="wrap blog-wrap">'
        '<nav class="blog-breadcrumb"><a href="/">홈</a> / '
        '<a href="/directory">전체 사이트모음</a> / 목록 관리 기록</nav>'
        '<div class="blog-heading"><h1>사이트모음 관리 기록과 주소 점검 범위</h1>'
        '<p>등록 사이트 수와 분야별 수정 내역, 주소 오류 제보 방법을 공개합니다.</p></div>'
        '<section class="seo-guidance"><h2>실제 등록 현황</h2>'
        '<p>링크위키 공개 목록에는 현재 ' + str(len(records)) + '개 사이트가 등록되어 있습니다. '
        '전체 목록 페이지의 마지막 중요한 편집 기록일은 ' + escape(edited) + '입니다.</p>'
        '<p><strong>편집 기록일은 외부 사이트 ' + str(len(records)) + '곳의 접속 확인일이 아닙니다.</strong> '
        '페이지 수정에는 링크 추가·분류·설명 개선도 포함됩니다. '
        '링크위키는 실시간 정상 운영·공식 소유권·보안을 보증하지 않습니다.</p>'
        '<p><a href="/directory">전체 사이트 이름과 주소 검색하기</a></p></section>'
        '<section class="seo-guidance"><h2>분야별 등록 수 및 페이지 수정일</h2>'
        '<p>아래 표는 링크위키 내부 콘텐츠의 날짜입니다. '
        '개별 도메인의 마지막 테스트나 변경 이력을 뜻하지 않습니다.</p>'
        '<table><thead><tr><th>분야</th><th>등록 사이트</th><th>페이지 수정일</th>'
        '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></section>'
        '<section class="seo-guidance"><h2>사이트 이동 전 확인할 사항</h2>'
        '<ol><li>목록에 표시된 도메인과 이동 후 주소창의 도메인을 비교하세요.</li>'
        '<li>로그인·결제·개인정보 제공 전에는 운영기관의 최신 안내를 확인하세요.</li>'
        '<li>자동 HTTP 점검 실패 한 번만으로 서비스 종료를 선언하지 않습니다.</li></ol>'
        '<p><a href="/guides/address-check">사이트 주소 확인 가이드</a>에서 '
        '구체적인 확인 방법을 볼 수 있습니다.</p></section>'
        '<section class="seo-guidance"><h2>잘못된 링크 수정 제보</h2>'
        '<p>잘못된 이름·주소·분류를 발견하면 '
        '<a href="https://t.me/linkwiki_info" rel="noopener noreferrer">'
        '링크위키 문의 채널</a>에 항목명과 공개 확인 근거를 알려주세요. '
        '비밀번호나 인증번호는 보내지 마세요.</p>'
        '<p>사이트 등록 순서는 인기순·안전성 평가가 아닙니다.</p></section>'
        '</div>'
    )
