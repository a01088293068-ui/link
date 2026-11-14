"""Grounded public explanation of directory edits and checking limitations."""
from datetime import date
from html import escape


def render_address_changes(records):
    """Show documented link changes whose destinations still match the catalogue."""
    changes = (
        (
            "2026-11-14", "대한민국 법원 전자소송포털",
            "기존 전자민원센터", "https://ecfs.scourt.go.kr/",
            "법원이 2025년 1월 31일 전자민원센터 서비스를 전자소송포털로 통합했습니다. 소송 관련 서식과 절차 안내를 이곳에서 찾을 수 있습니다.",
            "https://www.scourt.go.kr/work2025/helpinfo.html", "법원 통합 공지",
        ),
        (
            "2026-11-12", "대한상공회의소 코참넷",
            "https://www.korcham.net/", "https://www.korcham.net/nCham/Service/Main/appl/Main.asp",
            "링크위키에서 HTTPS 메인 페이지로 바로 이동하도록 등록 경로를 바꿨습니다.",
            "https://github.com/a01088293068-ui/link/pull/79", "등록 경로 변경 근거",
        ),
        (
            "2026-11-11", "국가통계포털 KOSIS",
            "https://kosis.kr/", "https://kosis.kr/index/index.do",
            "링크위키에 포털 첫 화면으로 직접 연결되는 경로를 등록했습니다.",
            "https://github.com/a01088293068-ui/link/pull/65", "등록 경로 변경 근거",
        ),
    )
    current_destinations = {record["url"] for record in records}
    entries = []
    for edited, name, previous, current, reason, source, source_label in changes:
        if current not in current_destinations:
            continue
        entries.append(
            f'<li><time datetime="{edited}">{edited}</time> · '
            f'<strong>{escape(name)}</strong><br>{escape(previous)} → '
            f'<a href="{escape(current)}">{escape(current)}</a>'
            f'<p>{escape(reason)} <a href="{escape(source)}">{escape(source_label)}</a></p></li>'
        )
    if not entries:
        return ""
    return (
        '<section class="seo-guidance"><h2>서비스 이전과 등록 주소 변경 기록</h2>'
        '<p>날짜는 링크위키에 반영한 날입니다. 서비스 이전과 같은 도메인 내 접속 경로 변경을 아래에서 확인할 수 있습니다.</p>'
        '<ul>' + "".join(entries) + '</ul></section>'
    )


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
        + render_address_changes(records) +
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
