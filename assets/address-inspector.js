/* LinkWiki address decomposition: local-only, zero network requests.
   A hostname display never establishes official ownership or safety. */
(function (root) {
  'use strict';
  function inspectAddress(raw) {
    const input = String(raw == null ? '' : raw).trim();
    if (!input || input.length > 2048) {
      return { ok: false, code: 'input', message: '주소를 입력해 주세요. (최대 2048자)' };
    }
    if (!/^https?:\/\//i.test(input)) {
      return { ok: false, code: 'protocol', message: 'https:// 또는 http://로 시작하는 전체 주소를 입력해 주세요.' };
    }
    let parsed;
    try { parsed = new URL(input); }
    catch (_) { return { ok: false, code: 'invalid', message: '주소 형식을 확인해 주세요.' }; }
    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname) {
      return { ok: false, code: 'invalid', message: '웹 주소가 아닙니다.' };
    }
    const userinfo = Boolean(parsed.username || parsed.password || /\/\/[^/]*@/.test(input));
    const unusualHost = parsed.hostname.startsWith('xn--') || parsed.hostname.includes('.xn--');
    const warnings = [];
    if (userinfo) warnings.push('주소의 @ 앞부분은 사용자 정보처럼 해석될 수 있습니다. 실제 접속 대상은 아래 호스트입니다.');
    if (parsed.protocol !== 'https:') warnings.push('HTTP 주소입니다. 전송이 암호화되지 않을 수 있습니다.');
    if (unusualHost) warnings.push('국제화 도메인(Punycode)이 포함되어 있습니다. 공식 안내와 철자를 대조하세요.');
    if (parsed.port && !['80', '443'].includes(parsed.port)) warnings.push('일반적이지 않은 접속 포트가 지정돼 있습니다.');
    return {
      ok: true, host: parsed.hostname, origin: parsed.origin,
      protocol: parsed.protocol.replace(':', '').toUpperCase(),
      path: (parsed.pathname || '/') + parsed.search + parsed.hash,
      warnings: warnings,
      note: '표시된 도메인은 브라우저가 해석한 접속 대상입니다. 공식 운영·안전·현재 접속 가능 여부는 검증하지 않습니다.'
    };
  }

  function init(doc) {
    const form = doc.getElementById('lw-address-form');
    const field = doc.getElementById('lw-address-input');
    const output = doc.getElementById('lw-address-result');
    if (!form || !field || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      const result = inspectAddress(field.value);
      output.replaceChildren();
      const para = function (label, value) {
        const p = doc.createElement('p');
        const strong = doc.createElement('strong');
        strong.textContent = label + ': ';
        p.append(strong, doc.createTextNode(value));
        output.append(p);
      };
      if (!result.ok) { para('입력 확인', result.message); return; }
      para('실제 접속 호스트', result.host);
      para('통신 방식', result.protocol);
      para('주소 나머지', result.path);
      for (const warning of result.warnings) para('주의', warning);
      para('안내', result.note);
    });
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = { inspectAddress, init };
  if (root && root.document) {
    if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', function () { init(root.document); });
    else init(root.document);
  }
})(typeof window !== 'undefined' ? window : null);
