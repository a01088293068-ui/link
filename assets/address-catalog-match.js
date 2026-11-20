/* LinkWiki catalog address matcher.
 * Compares a pasted URL with the public directory catalog only.
 * It does not establish ownership, safety, reachability or endorsement.
 */
(() => {
  'use strict';
  const form = document.getElementById('lw-catalog-match-form');
  const input = document.getElementById('lw-catalog-match-input');
  const output = document.getElementById('lw-catalog-match-result');
  if (!form || !input || !output) return;

  const hostOf = value => {
    const u = new URL(value);
    return u.hostname.toLowerCase().replace(/^www\./, '');
  };
  const pathOf = value => {
    const u = new URL(value);
    return (decodeURI(u.pathname || '/').replace(/\/$/, '') || '/');
  };
  const write = (tag, value) => {
    const node = document.createElement(tag);
    node.textContent = value;
    output.append(node);
    return node;
  };
  let catalogPromise = fetch('../assets/verified-directory.json', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' }
  }).then(response => {
    if (!response.ok) throw new Error('catalog unavailable');
    return response.json();
  }).then(rows => {
    if (!Array.isArray(rows)) throw new Error('invalid catalog');
    return rows.filter(row => row && typeof row.name === 'string' &&
      typeof row.url === 'string' && /^https:\/\//i.test(row.url));
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    output.replaceChildren();
    const raw = input.value.trim();
    let pasted;
    try {
      pasted = new URL(raw);
      if (!['https:', 'http:'].includes(pasted.protocol) ||
          !pasted.hostname || pasted.username || pasted.password) {
        throw new Error('invalid');
      }
    } catch (_) {
      write('p', '주소 형식을 확인해 주세요. https:// 또는 http://로 시작하는 전체 주소를 입력하세요.');
      return;
    }

    write('p', '등록 목록과 대조 중입니다…');
    try {
      const rows = await catalogPromise;
      output.replaceChildren();
      const host = hostOf(pasted.href);
      const path = pathOf(pasted.href);
      const sameHost = rows.filter(row => {
        try { return hostOf(row.url) === host; } catch (_) { return false; }
      });
      const exact = sameHost.filter(row => {
        try { return pathOf(row.url) === path; } catch (_) { return false; }
      });

      if (exact.length) {
        write('h3', '등록된 주소와 도메인·경로가 일치합니다');
        exact.slice(0, 5).forEach(row => {
          const p = write('p', row.name + ' · ' + row.category + ' · ' + host);
          p.className = 'lw-catalog-match-item';
        });
      } else if (sameHost.length) {
        write('h3', '등록된 사이트와 도메인은 같지만 경로가 다릅니다');
        sameHost.slice(0, 5).forEach(row => {
          write('p', row.name + ' · 등록 경로: ' + pathOf(row.url));
        });
        write('p', '받은 주소의 경로가 서비스에서 안내한 주소인지 별도로 확인하세요.');
      } else {
        write('h3', '등록 목록에서 일치하는 도메인을 찾지 못했습니다');
        write('p', '미등록 주소일 수 있습니다. 이 결과만으로 사기·피싱·위험 여부를 판단하지 않습니다.');
      }

      const link = document.createElement('a');
      link.href = '/directory?q=' + encodeURIComponent(host);
      link.textContent = '목록에서 이 도메인 검색';
      output.append(link);
      const note = write('p', '대조 기준은 링크위키 공개 목록의 등록 주소입니다. 공식 운영 주체·현재 접속 가능 여부·보안성을 인증하거나 보증하지 않습니다.');
      note.className = 'v6-muted';
    } catch (_) {
      output.replaceChildren();
      write('p', '주소 목록을 불러오지 못했습니다. 잠시 후 다시 시도하거나 전체 목록에서 직접 검색해 주세요.');
    }
  });
})();
