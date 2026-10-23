/* ═══════════════════════════════════════════════════════════════════════════
   BARRA DE SCROLL HORIZONTAL DUPLICADA ARRIBA
   Para cualquier contenedor con class="tabla-scroll-horizontal".
   Crea una barra de scroll arriba que se sincroniza con la de abajo.
   ═══════════════════════════════════════════════════════════════════════════ */

(function() {
  'use strict';

  function initScrollArriba(contenedor) {
    // Evitar duplicar si ya existe
    if (contenedor.parentElement.querySelector('.tabla-scroll-top-wrapper')) return;

    // Crear el wrapper de la barra superior
    const wrapper = document.createElement('div');
    wrapper.className = 'tabla-scroll-top-wrapper';

    // Crear el div interno que tendrá el ancho de la tabla
    const inner = document.createElement('div');
    inner.className = 'tabla-scroll-top-inner';

    wrapper.appendChild(inner);

    // Insertar la barra arriba del contenedor de la tabla
    contenedor.parentElement.insertBefore(wrapper, contenedor);

    // Sincronizar: barra superior → tabla
    wrapper.addEventListener('scroll', function() {
      contenedor.scrollLeft = wrapper.scrollLeft;
    });

    // Sincronizar: tabla → barra superior
    contenedor.addEventListener('scroll', function() {
      wrapper.scrollLeft = contenedor.scrollLeft;
    });

    // Ajustar el ancho del inner al ancho real de la tabla
    function ajustarAncho() {
      const tabla = contenedor.querySelector('table');
      if (tabla) {
        inner.style.width = tabla.scrollWidth + 'px';
      }
    }
    ajustarAncho();
    window.addEventListener('resize', ajustarAncho);

    // Re-ajustar cuando la tabla se recargue por AJAX
    const observer = new MutationObserver(ajustarAncho);
    observer.observe(contenedor, { childList: true, subtree: true });
  }

  function initAll() {
    // Buscar todos los contenedores con la clase
    const contenedores = document.querySelectorAll('.tabla-scroll-horizontal');
    contenedores.forEach(initScrollArriba);
  }

  // Inicializar
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // Re-inicializar cuando se añadan tablas por AJAX
  const observer = new MutationObserver(function(mutations) {
    let hayNuevas = false;
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.nodeType === 1) {
          if (node.matches && node.matches('.tabla-scroll-horizontal')) {
            hayNuevas = true;
          }
          if (node.querySelectorAll && node.querySelectorAll('.tabla-scroll-horizontal').length) {
            hayNuevas = true;
          }
        }
      });
    });
    if (hayNuevas) initAll();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  } else {
    observer.observe(document.body, { childList: true, subtree: true });
  }

})();