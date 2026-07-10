/* ─── Botón flotante "Volver arriba" ───────────────────────────────────── */
(function() {
  const btnScrollTop = document.getElementById('btn-scroll-top');

  if (!btnScrollTop) return;

  window.addEventListener('scroll', function() {
    // Mostrar el botón cuando el scroll supera la mitad de la ventana
    const mitadPantalla = window.innerHeight / 2;

    if (window.scrollY > mitadPantalla) {
      btnScrollTop.classList.add('visible');
    } else {
      btnScrollTop.classList.remove('visible');
    }
  });
})();