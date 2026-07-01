/* ─── Estados de carga en formularios UPTCER ────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {

  const SPINNER = `
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"
      style="animation:girar 0.7s linear infinite;flex-shrink:0;"
      xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2"
        stroke-dasharray="25" stroke-dashoffset="10" opacity="0.4"/>
      <path d="M8 2a6 6 0 0 1 6 6" stroke="currentColor"
        stroke-width="2" stroke-linecap="round"/>
    </svg>
  `;

  if (!document.getElementById('style-girar')) {
    const style = document.createElement('style');
    style.id = 'style-girar';
    style.textContent = `@keyframes girar { to { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }

  document.querySelectorAll('form').forEach(form => {
    if (form.dataset.sinCarga !== undefined) return;
    if (form.method.toLowerCase() === 'get') return;

    form.addEventListener('submit', function() {
      const btn = form.querySelector('[type="submit"]:not([data-sin-carga])') ||
                  form.querySelector('button:not([type="button"]):not([data-sin-carga])');

      if (!btn) return;

      const textoOriginal = btn.innerHTML;
      const anchoOriginal = btn.offsetWidth;

      btn.style.minWidth = anchoOriginal + 'px';
      btn.disabled       = true;
      btn.style.opacity  = '0.75';
      btn.style.cursor   = 'not-allowed';

      const textoVisible = Array.from(btn.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent.trim())
        .filter(Boolean)
        .join(' ') || 'Procesando';

      btn.innerHTML = `
        <span style="display:inline-flex;align-items:center;gap:8px;">
          ${SPINNER}
          <span>${textoVisible}...</span>
        </span>
      `;

      form.querySelectorAll('[type="submit"], button:not([type="button"])').forEach(b => {
        if (b !== btn) b.disabled = true;
      });

      setTimeout(() => {
        if (document.body.contains(btn)) {
          btn.disabled       = false;
          btn.innerHTML      = textoOriginal;
          btn.style.opacity  = '';
          btn.style.cursor   = '';
          btn.style.minWidth = '';
        }
      }, 10000);
    });
  });
});