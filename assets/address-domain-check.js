/* Catalog-backed URL comparison. It performs no network requests. */
(() => {
  'use strict';
  const form = document.getElementById('lw-address-check-form');
  const input = document.getElementById('lw-address-check-input');
  const output = document.getElementById('lw-address-check-result');
  const catalog = document.getElementById('v6-results');
  if (!form || !input || !output || !catalog) return;
  const entries = [...catalog.querySelectorAll('article.v6-card')].map(card => {
    const name = card.querySelector('h3')?.textContent.trim() || '';
    const category = card.querySelector('small')?.textContent.trim() || '';
    const link = card.querySelector('a[href]');
    if (!name || !link) return null;
    try {
      const url = new URL(link.href);
      return {name, category, url: url.href, host: normalizeHost(url.hostname)};
    } catch (_) { return null; }
  }).filter(Boolean);
  function normalizeHost(host) {
    return String(host || '').toLowerCase().replace(/^www\./, '').replace(/\.$/, '');
  }
  function add(parent, tag, value, className) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
    parent.append(node);
    return node;
  }
  function parseAddress(raw) {
    const value = String(raw || '').trim();
    if (!value) throw new Error('확인할 주소를 입력하세요.');
    if (value.length > 2048 || /[\s\\]/.test(value)) throw new Error('주소 길이나 공백을 확인하세요. URL 전체를 공백 없이 입력하세요.');
    const explicitScheme = /^[a-z][a-z0-9+.-]*:/i.test(value);
    let url;
    try { url = new URL(explicitScheme ? value : 'https://' + value); }
    catch (_) { throw new Error('올바른 웹 주소 형식이 아닙니다. 도메인 또는 http(s) URL을 입력하세요.'); }
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('웹 주소는 http 또는 https만 대조할 수 있습니다.');
    if (url.username || url.password) throw new Error('주소에 사용자 이름이나 비밀번호가 포함되어 있습니다. 해당 주소를 열지 말고 출처를 다시 확인하세요.');
    if (!url.hostname || url.hostname.indexOf('.') < 1) throw new Error('완전한 도메인 주소를 입력하세요.');
    const host = normalizeHost(url.hostname);
    return {url, host, isIp: /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host) || host.includes(':'), punycode: host.split('.').some(label => label.startsWith('xn--'))};
  }
  function render(raw) {
    output.replaceChildren();
    let parsed;
    try { parsed = parseAddress(raw); }
    catch (error) { add(output, 'p', error.message, 'lw-check-warning'); return; }
    const matches = entries.filter(entry => entry.host === parsed.host);
    const warnings = [];
    if (parsed.url.protocol !== 'https:') warnings.push('HTTPS가 아닌 주소입니다. 로그인이나 결제 정보를 입력하기 전에 공식 안내를 확인하세요.');
    if (parsed.url.port && !['80', '443'].includes(parsed.url.port)) warnings.push('일반적이지 않은 포트 번호가 포함되어 있습니다.');
    if (parsed.punycode) warnings.push('국제화 도메인(Punycode)입니다. 화면에 보이는 문자와 실제 도메인이 다를 수 있으니 주의하세요.');
    if (parsed.isIp) warnings.push('IP 주소로 직접 접속하는 형태입니다. 운영기관의 공식 도메인인지 별도로 확인하세요.');
    if (matches.length) {
      add(output, 'p', '등록 목록에서 도메인이 일치하는 항목을 찾았습니다.', 'lw-check-match');
      matches.forEach(entry => {
        const card = add(output, 'div', '', 'lw-check-entry');
        add(card, 'strong', entry.name + (entry.category ? ' · ' + entry.category : ''));
        add(card, 'p', '등록 주소: ' + entry.url);
        const link = document.createElement('a');
        link.href = entry.url; link.target = '_blank'; link.rel = 'noopener noreferrer external';
        link.textContent = '등록된 주소 열기'; card.append(link);
      });
    } else {
      add(output, 'p', '등록 목록에서 일치하는 도메인을 찾지 못했습니다.', 'lw-check-warning');
      add(output, 'p', '목록에 없거나 별도 하위 도메인일 수 있습니다. 일치하지 않는다는 사실만으로 위험하다고 단정할 수 없습니다.');
    }
    if (warnings.length) {
      const list = document.createElement('ul');
      warnings.forEach(warning => add(list, 'li', warning));
      output.append(list);
    }
    add(output, 'p', '대조 도메인: ' + parsed.host, 'lw-check-domain');
    add(output, 'p', '이 결과는 링크위키 등록 목록과 URL 형식만 비교합니다. 운영 주체, 현재 접속 가능 여부, 피싱·악성코드 여부 또는 안전성을 인증하지 않습니다.', 'v6-muted');
  }
  form.addEventListener('submit', event => { event.preventDefault(); render(input.value); });
})();
