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

  // Hacer que los elementos internos no capturen el mouse
  // pero el botón de cerrar SÍ debe seguir funcionando
  toast.querySelectorAll('i, .toast-cuerpo, .toast-icono, .toast-titulo, .toast-mensaje').forEach(el => {
    el.style.pointerEvents = 'none';
  });

  // Animar entrada
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      toast.classList.add('visible');
    });
  });

  // ─── Sistema de pausa/reanudación ──────────────────────────────────────
  let tiempoRestante = duracion;
  let temporizador = null;

  function iniciarTemporizador() {
    temporizador = setTimeout(() => {
      cerrarToast(toast);
    }, tiempoRestante);
  }

  // Cerrar al hacer click en X
  toast.querySelector('.toast-cerrar').addEventListener('click', (e) => {
    e.stopPropagation();
    if (temporizador) clearTimeout(temporizador);
    cerrarToast(toast);
  });

  // Pausar al pasar el mouse
  toast.addEventListener('mouseenter', () => {
    if (temporizador) {
      clearTimeout(temporizador);
      temporizador = null;
    }
  });

  // Reanudar al quitar el mouse
  toast.addEventListener('mouseleave', () => {
    if (!temporizador) {
      temporizador = setTimeout(() => {
        cerrarToast(toast);
      }, tiempoRestante);
    }
  });

  // Iniciar temporizador
  iniciarTemporizador();
}

function cerrarToast(toast) {
  toast.classList.remove('visible');
  toast.classList.add('saliendo');
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
    }
  }, 300);
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