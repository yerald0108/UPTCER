/* ─── Búsqueda en tiempo real con AJAX ────────────────────────────────── */
(function() {
  const formFiltros = document.getElementById('form-filtros');
  if (!formFiltros) return;

  const contenedorTabla = document.getElementById('contenedor-tabla');
  if (!contenedorTabla) return;

  let timeoutBusqueda;

  // Obtener todos los campos del formulario
  const campos = formFiltros.querySelectorAll('input, select');

  function aplicarFiltros() {
    clearTimeout(timeoutBusqueda);

    timeoutBusqueda = setTimeout(() => {
      const formData = new FormData(formFiltros);
      const params = new URLSearchParams();

      // Solo agregar parámetros con valor
      for (const [key, value] of formData.entries()) {
        if (value.trim()) {
          params.set(key, value.trim());
        }
      }

      const url = `${window.location.pathname}?${params.toString()}`;

      // Actualizar URL sin recargar
      history.pushState({}, '', url);

      // Hacer petición AJAX
      fetch(url, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.text())
      .then(html => {
        contenedorTabla.innerHTML = html;

        // Re-inicializar íconos de Lucide
        if (typeof lucide !== 'undefined') {
          lucide.createIcons();
        }
      });
    }, 300);
  }

  // Asignar eventos a todos los campos
  campos.forEach(campo => {
    if (campo.tagName === 'SELECT') {
      campo.addEventListener('change', aplicarFiltros);
    } else if (campo.tagName === 'INPUT') {
      campo.addEventListener('input', aplicarFiltros);
    }
  });
})();