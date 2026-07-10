/* ─── Función de impresión de documentos ──────────────────────────────────── */
(function() {
  /**
   * Imprime un documento clonándolo en una ventana nueva.
   * 
   * @param {Object} config - Configuración de impresión
   * @param {string} config.selector - Selector CSS del elemento a imprimir (ej: '.f43-hoja')
   * @param {string} config.titulo - Título de la ventana de impresión
   * @param {Object} [config.estilos] - Estilos CSS personalizados para la impresión
   */
  window.imprimirDocumento = function(config) {
    const { selector, titulo, estilos } = config;
    
    const hojaOriginal = document.querySelector(selector);
    if (!hojaOriginal) {
      console.error('No se encontró el elemento:', selector);
      return;
    }

    const clon = hojaOriginal.cloneNode(true);

    // Resetear zoom y estilos en el clon
    clon.style.zoom = '1';
    clon.style.transform = 'none';
    clon.style.width = '210mm';
    clon.style.margin = '0 auto';
    clon.style.padding = '5mm';
    clon.style.boxShadow = 'none';
    clon.style.border = 'none';
    clon.style.position = 'static';

    // Estilos base de impresión
    const estilosBase = `
      @page { size: A4; margin: 3mm; }
      body { 
        margin: 0; 
        padding: 3mm; 
        display: flex; 
        justify-content: center; 
        background: white; 
        font-family: Arial, sans-serif;
      }
      table { border-collapse: collapse; width: 100%; }
      th, td { border: 1px solid #000; padding: 2px 4px; font-size: 10px; }
      th { background-color: #f0f0f0; font-weight: bold; text-align: center; }
      input, select, textarea { 
        border: none !important; 
        background: transparent !important; 
        color: black !important; 
        font-size: 10px !important; 
        font-family: inherit !important; 
        width: 100%; 
      }
      .no-print { display: none !important; }
      a { color: black; text-decoration: none; }
    `;

    // Crear ventana nueva
    const ventana = window.open('', '_blank', 'width=800,height=600');
    ventana.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>${titulo} — Ministerio de Comunicaciones</title>
        <style>
          ${estilosBase}
          ${estilos || ''}
        </style>
      </head>
      <body>
        ${clon.outerHTML}
      </body>
      </html>
    `);
    ventana.document.close();
    ventana.focus();
    setTimeout(() => ventana.print(), 500);
  };
})();