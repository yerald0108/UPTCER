/* ─── Sistema de Toasts UPTCER ───────────────────────────────────────────── */

const ICONOS_TOAST = {
  success: 'check-circle',
  error:   'x-circle',
  warning: 'alert-triangle',
  info:    'info',
};

const TITULOS_TOAST = {
  success: 'Operación exitosa',
  error:   'Error',
  warning: 'Advertencia',
  info:    'Información',
};

function mostrarToast({ tipo = 'info', titulo = '', mensaje = '', duracion = 4000 }) {
  let contenedor = document.getElementById('toast-contenedor');
  if (!contenedor) {
    contenedor = document.createElement('div');
    contenedor.id = 'toast-contenedor';
    contenedor.className = 'toast-contenedor';
    document.body.appendChild(contenedor);
  }

  const icono   = ICONOS_TOAST[tipo]  || 'info';
  const tituloFinal = titulo || TITULOS_TOAST[tipo] || 'Información';

  const toast = document.createElement('div');
  toast.className = `toast toast-${tipo}`;
  toast.style.setProperty('--toast-duracion', `${duracion}ms`);

  toast.innerHTML = `
    <i data-lucide="${icono}" class="toast-icono"></i>
    <div class="toast-cuerpo">
      <div class="toast-titulo">${tituloFinal}</div>
      ${mensaje ? `<div class="toast-mensaje">${mensaje}</div>` : ''}
    </div>
    <button class="toast-cerrar" aria-label="Cerrar notificación">
      <i data-lucide="x" style="width:16px;height:16px;"></i>
    </button>
  `;

  contenedor.appendChild(toast);
  lucide.createIcons({ nodes: [toast] });

  // Animar entrada
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      toast.classList.add('visible');
    });
  });

  // Cerrar al hacer click en X
  toast.querySelector('.toast-cerrar').addEventListener('click', () => {
    cerrarToast(toast);
  });

  // Auto cerrar
  const temporizador = setTimeout(() => cerrarToast(toast), duracion);

  // Pausar al pasar el mouse
  toast.addEventListener('mouseenter', () => clearTimeout(temporizador));
  toast.addEventListener('mouseleave', () => {
    setTimeout(() => cerrarToast(toast), 1000);
  });
}

function cerrarToast(toast) {
  toast.classList.remove('visible');
  toast.classList.add('saliendo');
  toast.addEventListener('transitionend', () => toast.remove(), { once: true });
}

// ─── Leer mensajes de Django desde el DOM ────────────────────────────────────
function inicializarToasts() {
  const contenedorMensajes = document.getElementById('django-messages');
  if (!contenedorMensajes) return;

  const mensajes = contenedorMensajes.querySelectorAll('[data-toast]');
  mensajes.forEach((el, index) => {
    setTimeout(() => {
      mostrarToast({
        tipo:    el.dataset.tipo    || 'info',
        titulo:  el.dataset.titulo  || '',
        mensaje: el.dataset.mensaje || '',
      });
    }, index * 150);
  });
}

document.addEventListener('DOMContentLoaded', inicializarToasts);

/* ─── Estados de carga en formularios ───────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {

  // SVG del spinner
  const SPINNER = `
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none"
      style="animation:girar 0.7s linear infinite;flex-shrink:0;"
      xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" stroke-dasharray="25" stroke-dashoffset="10" opacity="0.4"/>
      <path d="M8 2a6 6 0 0 1 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `;

  // Agregar keyframe de rotación al documento
  if (!document.getElementById('style-girar')) {
    const style = document.createElement('style');
    style.id = 'style-girar';
    style.textContent = `@keyframes girar { to { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
  }

  // Interceptar todos los formularios
  document.querySelectorAll('form').forEach(form => {

    // Excluir formularios que no deben bloquear (filtros, búsquedas)
    if (form.dataset.sinCarga !== undefined) return;
    if (form.method.toLowerCase() === 'get') return;

    form.addEventListener('submit', function(e) {

      // Buscar el botón que disparó el envío
      const btn = form.querySelector('[type="submit"]:not([data-sin-carga])') ||
                  form.querySelector('button:not([type="button"]):not([data-sin-carga])');

      if (!btn) return;

      // Guardar el contenido original del botón
      const textoOriginal = btn.innerHTML;
      const anchoOriginal  = btn.offsetWidth;

      // Fijar el ancho para que no cambie al reemplazar el contenido
      btn.style.minWidth = anchoOriginal + 'px';

      // Deshabilitar el botón
      btn.disabled = true;
      btn.style.opacity = '0.75';
      btn.style.cursor  = 'not-allowed';

      // Extraer el texto visible del botón (sin iconos SVG)
      const textoVisible = Array.from(btn.childNodes)
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent.trim())
        .filter(Boolean)
        .join(' ') || 'Procesando';

      // Mostrar spinner + texto
      btn.innerHTML = `
        <span style="display:inline-flex;align-items:center;gap:8px;">
          ${SPINNER}
          <span>${textoVisible}...</span>
        </span>
      `;

      // Deshabilitar todos los demás botones submit del formulario
      form.querySelectorAll('[type="submit"], button:not([type="button"])').forEach(b => {
        if (b !== btn) b.disabled = true;
      });

      // Safety: restaurar si la página no navega en 10 segundos (error de red)
      setTimeout(() => {
        if (document.body.contains(btn)) {
          btn.disabled   = false;
          btn.innerHTML  = textoOriginal;
          btn.style.opacity = '';
          btn.style.cursor  = '';
          btn.style.minWidth = '';
        }
      }, 10000);

    });
  });

  // Deshabilitar botones que usan confirmarAccion() — se manejan por callback
  // Los formularios con modal de confirmación ya tienen su propio flujo
});