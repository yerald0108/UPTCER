/* ═══════════════════════════════════════════════════════════════════════════
   DOBLE CLICK EN FILA → ABRIR DETALLE
   Funciona en cualquier <tr> con atributo data-href.
   Se aplica globalmente con delegación de eventos, así que funciona
   aunque la tabla se recargue por AJAX.

   Uso en el template:
     <tr class="fila-clicable"
         data-href="{% url 'app:detalle' pk=obj.pk %}"
         title="Doble clic para abrir">
   ═══════════════════════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  document.addEventListener('dblclick', function (e) {
    // Ignorar si el doble click fue sobre un elemento interactivo
    if (e.target.closest('a, button, input, select, textarea, label, [role="button"]')) {
      return;
    }

    // Buscar la fila más cercana con data-href
    const fila = e.target.closest('tr[data-href]');
    if (!fila) return;

    const url = fila.dataset.href;
    if (url) {
      window.location.href = url;
    }
  });

  // Añadir cursor pointer automáticamente a las filas con data-href
  // (aunque el template no tenga la clase fila-clicable)
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('tr[data-href]').forEach(function(tr) {
      tr.style.cursor = 'pointer';
      if (!tr.title) tr.title = 'Doble clic para abrir';
    });
  });

  // Re-aplicar cursor cuando la tabla se recargue por AJAX
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.nodeType === 1) {
          if (node.matches && node.matches('tr[data-href]')) {
            node.style.cursor = 'pointer';
            if (!node.title) node.title = 'Doble clic para abrir';
          }
          if (node.querySelectorAll) {
            node.querySelectorAll('tr[data-href]').forEach(function(tr) {
              tr.style.cursor = 'pointer';
              if (!tr.title) tr.title = 'Doble clic para abrir';
            });
          }
        }
      });
    });
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  } else {
    observer.observe(document.body, { childList: true, subtree: true });
  }

})();