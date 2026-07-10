/* ─── Control de zoom del documento ──────────────────────────────────── */
(function() {
  const ZOOM_MIN     = 70;
  const ZOOM_MAX     = 130;
  const ZOOM_DEFECTO = 100;

  // Detectar automáticamente el elemento a ampliar
  const hoja = document.querySelector('.f43-hoja') || document.querySelector('.licencia-hoja');
  if (!hoja) return;

  // Clave única según la página
  const pagina = document.body.dataset.pagina || 'default';
  const ZOOM_CLAVE = `uptcer_zoom_${pagina}`;

  window.aplicarZoom = function(nivel) {
    hoja.style.zoom = (nivel / 100);
    const indicador = document.getElementById('zoom-nivel');
    if (indicador) indicador.textContent = nivel + '%';
    localStorage.setItem(ZOOM_CLAVE, nivel);
  };

  window.cambiarZoom = function(delta) {
    const actual = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO);
    const nuevo  = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, actual + delta));
    window.aplicarZoom(nuevo);
    if (nuevo === ZOOM_MIN && delta < 0 && typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'info', mensaje: 'Tamaño mínimo alcanzado.', duracion: 2000 });
    }
    if (nuevo === ZOOM_MAX && delta > 0 && typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'info', mensaje: 'Tamaño máximo alcanzado.', duracion: 2000 });
    }
  };

  window.resetearZoom = function() {
    window.aplicarZoom(ZOOM_DEFECTO);
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'info', mensaje: 'Tamaño del documento restablecido.', duracion: 2000 });
    }
  };

  // Restaurar zoom guardado al cargar
  document.addEventListener('DOMContentLoaded', () => {
    const guardado = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO);
    window.aplicarZoom(guardado);
  });
})();