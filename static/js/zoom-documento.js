/* ═══════════════════════════════════════════════════════════════════════════
   Control de zoom del documento + impresión limpia
   ═══════════════════════════════════════════════════════════════════════════
   API global:
     window.cambiarZoom(delta)      → suma/resta delta al zoom actual
     window.resetearZoom()          → vuelve al 100%
     window.aplicarZoom(nivel)      → fija un nivel concreto
     window.imprimirDocumento()     → resetea zoom a 100% e imprime

   Selectores de documento soportados (en este orden):
     [data-zoom-target]   → el que se indique explícitamente
     .f43-documento       → F43 (3 páginas Letter)
     .licencia-hoja       → licencia (1 página A4)
     .f43-hoja            → F43 legado (1 página A4)
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const ZOOM_MIN     = 100;   // ya no se puede reducir
  const ZOOM_MAX     = 130;   // máximo permitido
  const ZOOM_DEFECTO = 100;

  /* ─── Detectar todos los documentos a ampliar ──────────────────────────── */
  function obtenerDocumentos() {
    const explicitos = document.querySelectorAll('[data-zoom-target]');
    if (explicitos.length) {
      return Array.from(explicitos).map(el =>
        el.dataset.zoomTarget
          ? document.querySelector(el.dataset.zoomTarget)
          : el
      ).filter(Boolean);
    }

    const docs = [
      ...document.querySelectorAll('.f43-documento'),
      ...document.querySelectorAll('.licencia-hoja'),
      ...document.querySelectorAll('.f43-hoja'),
    ];

    return docs;
  }

  const documentos = obtenerDocumentos();
  if (!documentos.length) return;

  /* ─── Clave única según la página ──────────────────────────────────────── */
  const pagina = document.body.dataset.pagina || 'default';
  const ZOOM_CLAVE = `uptcer_zoom_${pagina}`;

  /* ─── Aplicar zoom ─────────────────────────────────────────────────────── */
  window.aplicarZoom = function (nivel) {
    nivel = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, parseInt(nivel, 10) || ZOOM_DEFECTO));

    documentos.forEach(doc => {
      doc.style.zoom = (nivel / 100);
      doc.style.transform = '';
      doc.style.transformOrigin = '';
      doc.style.marginBottom = '';
    });

    const indicador = document.getElementById('zoom-nivel');
    if (indicador) indicador.textContent = nivel + '%';

    // Deshabilitar botón "+" si llegamos al máximo
    const btnMas = document.getElementById('zoom-btn-mas');
    if (btnMas) {
      const enMax = nivel >= ZOOM_MAX;
      btnMas.disabled      = enMax;
      btnMas.style.opacity = enMax ? '0.4' : '';
      btnMas.style.cursor  = enMax ? 'not-allowed' : 'pointer';
      btnMas.title         = enMax ? 'Tamaño máximo alcanzado' : 'Aumentar tamaño';
    }

    // Deshabilitar botón "−" si llegamos al mínimo
    const btnMenos = document.getElementById('zoom-btn-menos');
    if (btnMenos) {
      const enMin = nivel <= ZOOM_MIN;
      btnMenos.disabled      = enMin;
      btnMenos.style.opacity = enMin ? '0.4' : '';
      btnMenos.style.cursor  = enMin ? 'not-allowed' : 'pointer';
      btnMenos.title         = enMin ? 'Tamaño mínimo alcanzado' : 'Reducir tamaño';
    }

    try {
      localStorage.setItem(ZOOM_CLAVE, nivel);
    } catch (e) { /* silencioso si localStorage está lleno */ }
  };

  /* ─── Cambiar zoom (sumar/restar) ──────────────────────────────────────── */
  window.cambiarZoom = function (delta) {
    let actual;
    try {
      actual = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO, 10);
    } catch (e) {
      actual = ZOOM_DEFECTO;
    }

    const nuevo = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, actual + delta));
    window.aplicarZoom(nuevo);

    if (nuevo === ZOOM_MAX && delta > 0 && typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'info', mensaje: 'Tamaño máximo alcanzado.', duracion: 2000 });
    }

    if (nuevo === ZOOM_MIN && delta < 0 && typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'info', mensaje: 'Tamaño mínimo alcanzado.', duracion: 2000 });
    }
  };

  /* ─── Resetear ─────────────────────────────────────────────────────────── */
  window.resetearZoom = function () {
    window.aplicarZoom(ZOOM_DEFECTO);
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'info', mensaje: 'Tamaño del documento restablecido.', duracion: 2000 });
    }
  };

  /* ─── Restaurar zoom guardado al cargar ────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    let guardado;
    try {
      guardado = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO, 10);
    } catch (e) {
      guardado = ZOOM_DEFECTO;
    }
    window.aplicarZoom(guardado);
  });

  /* ═══════════════════════════════════════════════════════════════════════
     IMPRESIÓN LIMPIA
     ═══════════════════════════════════════════════════════════════════════ */

  /* ─── Resetear zoom antes de imprimir (Ctrl+P, botón del navegador) ───── */
  window.addEventListener('beforeprint', function () {
    // Forzar zoom a 100% sin toast
    documentos.forEach(doc => {
      doc.style.zoom = 1;
      doc.style.transform = '';
      doc.style.transformOrigin = '';
      doc.style.marginBottom = '';
    });
    const indicador = document.getElementById('zoom-nivel');
    if (indicador) indicador.textContent = '100%';
  });

  /* ─── Restaurar zoom guardado después de imprimir ─────────────────────── */
  window.addEventListener('afterprint', function () {
    let guardado;
    try {
      guardado = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO, 10);
    } catch (e) {
      guardado = ZOOM_DEFECTO;
    }
    window.aplicarZoom(guardado);
  });

  /* ─── Función para usar en los botones "Imprimir / PDF" ───────────────── */
  window.imprimirDocumento = function () {
    // Resetear zoom a 100% antes de imprimir
    documentos.forEach(doc => {
      doc.style.zoom = 1;
      doc.style.transform = '';
      doc.style.transformOrigin = '';
      doc.style.marginBottom = '';
    });
    const indicador = document.getElementById('zoom-nivel');
    if (indicador) indicador.textContent = '100%';

    // Esperar un tick para que el navegador aplique el zoom, luego imprimir
    setTimeout(function () {
      window.print();

      // Restaurar el zoom guardado después de imprimir
      setTimeout(function () {
        let guardado;
        try {
          guardado = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO, 10);
        } catch (e) {
          guardado = ZOOM_DEFECTO;
        }
        window.aplicarZoom(guardado);
      }, 500);
    }, 150);
  };

    /* ═══════════════════════════════════════════════════════════════════════
     IMPRESIÓN LIMPIA
     ═══════════════════════════════════════════════════════════════════════ */

  /* ─── Resetear zoom antes de imprimir (Ctrl+P o botón) ──────────────── */
  window.addEventListener('beforeprint', function () {
    documentos.forEach(doc => {
      doc.style.zoom = 1;
      doc.style.transform = '';
      doc.style.transformOrigin = '';
      doc.style.marginBottom = '';
    });
    const indicador = document.getElementById('zoom-nivel');
    if (indicador) indicador.textContent = '100%';
  });

  /* ─── Restaurar zoom después de imprimir ────────────────────────────── */
  window.addEventListener('afterprint', function () {
    let guardado;
    try {
      guardado = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO, 10);
    } catch (e) {
      guardado = ZOOM_DEFECTO;
    }
    window.aplicarZoom(guardado);
  });

  /* ─── Función global para el botón "Imprimir / PDF" ─────────────────── */
  window.imprimirDocumento = function () {
    // Resetear zoom a 100%
    documentos.forEach(doc => {
      doc.style.zoom = 1;
      doc.style.transform = '';
      doc.style.transformOrigin = '';
      doc.style.marginBottom = '';
    });
    const indicador = document.getElementById('zoom-nivel');
    if (indicador) indicador.textContent = '100%';

    // Esperar un tick y luego imprimir
    setTimeout(function () {
      window.print();

      // Restaurar zoom después de imprimir
      setTimeout(function () {
        let guardado;
        try {
          guardado = parseInt(localStorage.getItem(ZOOM_CLAVE) || ZOOM_DEFECTO, 10);
        } catch (e) {
          guardado = ZOOM_DEFECTO;
        }
        window.aplicarZoom(guardado);
      }, 500);
    }, 150);
  };

})();