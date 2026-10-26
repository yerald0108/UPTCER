/* ─── Función de impresión de documentos ────────────────────────────────────
   Usa window.open() con SOLO el CSS del documento (impresion-f43.css).
   URL ABSOLUTA para que el CSS cargue incluso en about:blank.
   Espera a que el CSS cargue antes de imprimir.
   ──────────────────────────────────────────────────────────────────────── */

(function() {
  'use strict';

  function obtenerDocumento() {
    const explicit = document.querySelector('[data-zoom-target]');
    if (explicit) {
      const sel = explicit.dataset.zoomTarget;
      return sel ? document.querySelector(sel) : explicit;
    }
    return (
      document.querySelector('.f43-documento') ||
      document.querySelector('.licencia-hoja') ||
      document.querySelector('.f43-hoja')
    );
  }

  /* ─── URL ABSOLUTA del CSS de impresión ───────────────────────────────── */
  function getCssImpresionUrl() {
    const staticUrl = window.STATIC_URL || '/static/';
    const origin    = window.location.origin;
    return `${origin}${staticUrl}css/impresion-f43.css`;
  }

  /* ─── Imprimir cuando el CSS esté cargado ─────────────────────────────── */
  function imprimirCuandoCargue(ventana) {
    const links = ventana.document.querySelectorAll('link[rel="stylesheet"]');
    let pendientes = links.length;

    function imprimir() {
      ventana.focus();
      ventana.print();
      ventana.onafterprint = function () { ventana.close(); };
    }

    if (pendientes === 0) {
      setTimeout(imprimir, 300);
      return;
    }

    links.forEach(link => {
      link.onload = link.onerror = function () {
        pendientes--;
        if (pendientes === 0) {
          setTimeout(imprimir, 300);
        }
      };
    });

    // Fallback: si después de 2s no ha cargado, imprimir igual
    setTimeout(function () {
      if (pendientes > 0) {
        imprimir();
      }
    }, 2000);
  }

  /* ─── Impresión limpia con window.open() ─────────────────────────────── */
  function imprimirLimpio() {
    const docEl = obtenerDocumento();
    if (!docEl) {
      console.error('No se encontró el documento para imprimir.');
      return;
    }

    const clon = docEl.cloneNode(true);
    clon.style.zoom      = '1';
    clon.style.transform = 'none';

    const cssUrl = getCssImpresionUrl();
    console.log('CSS de impresión:', cssUrl);

    const ventana = window.open('', '_blank');
    if (!ventana) {
      alert('El navegador bloqueó la ventana de impresión.\n\nPermite las ventanas emergentes para este sitio e inténtalo de nuevo.');
      return;
    }

    ventana.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>Imprimir — Ministerio de Comunicaciones</title>
        <link rel="stylesheet" href="${cssUrl}">
      </head>
      <body>
        ${clon.outerHTML}
      </body>
      </html>
    `);

    ventana.document.close();

    // Esperar a que el CSS cargue antes de imprimir
    ventana.onload = function () {
      imprimirCuandoCargue(ventana);
    };
  }

  /* ─── Modo por selector ──────────────────────────────────────────────── */
  function imprimirPorSelector(config) {
    const { selector, titulo, estilos } = config;
    const hojaOriginal = document.querySelector(selector);
    if (!hojaOriginal) {
      console.error('No se encontró el elemento:', selector);
      return;
    }

    const clon = hojaOriginal.cloneNode(true);
    clon.style.zoom      = '1';
    clon.style.transform = 'none';

    const cssUrl = getCssImpresionUrl();

    const ventana = window.open('', '_blank', 'width=800,height=600');
    ventana.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>${titulo || 'Documento'}</title>
        <link rel="stylesheet" href="${cssUrl}">
        ${estilos ? `<style>${estilos}</style>` : ''}
      </head>
      <body>
        ${clon.outerHTML}
      </body>
      </html>
    `);
    ventana.document.close();
    ventana.focus();
    setTimeout(() => ventana.print(), 800);
  }

  /* ─── Función principal ──────────────────────────────────────────────── */
  window.imprimirDocumento = function (config) {
    if (!config || !config.selector) {
      imprimirLimpio();
    } else {
      imprimirPorSelector(config);
    }
  };

})();