(()=>{
  const toggle=document.querySelector('.mobile-menu-toggle');
  const menu=document.getElementById('mobile-primary-nav');
  if(!toggle||!menu)return;
  const close=()=>{
    menu.classList.remove('is-open');
    toggle.setAttribute('aria-expanded','false');
    toggle.setAttribute('aria-label','메뉴 열기');
    const icon=toggle.querySelector('.menu-toggle-icon');
    if(icon)icon.textContent='☰';
  };
  toggle.addEventListener('click',()=>{
    const open=toggle.getAttribute('aria-expanded')!=='true';
    if(!open){close();return;}
    menu.classList.add('is-open');
    toggle.setAttribute('aria-expanded','true');
    toggle.setAttribute('aria-label','메뉴 닫기');
    const icon=toggle.querySelector('.menu-toggle-icon');
    if(icon)icon.textContent='×';
  });
  menu.addEventListener('click',event=>{if(event.target.closest('a'))close();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')close();});
  document.addEventListener('click',event=>{if(!event.target.closest('.top'))close();});
  window.matchMedia('(min-width:681px)').addEventListener('change',event=>{if(event.matches)close();});
})();
