/* ─── Sistema de modales de confirmación UPTCER ──────────────────────────── */

let _modalCallback = null;
let _modalFormTarget = null;

// ─── Abrir modal genérico ─────────────────────────────────────────────────────
function abrirModal(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.add('visible');
  document.body.style.overflow = 'hidden';

  // Foco en el botón de confirmar para accesibilidad
  setTimeout(() => {
    const btnConfirmar = overlay.querySelector('[data-confirmar]');
    if (btnConfirmar) btnConfirmar.focus();
  }, 250);
}

function cerrarModal(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  overlay.classList.remove('visible');
  document.body.style.overflow = '';
  _modalCallback    = null;
  _modalFormTarget  = null;
}

// ─── Modal de confirmación dinámico ──────────────────────────────────────────
function confirmarAccion({
  titulo      = '¿Está seguro?',
  mensaje     = 'Esta acción no se puede deshacer.',
  labelConfirmar = 'Confirmar',
  tipo        = 'peligro',
  icono       = 'alert-triangle',
  onConfirmar = null,
  formId      = null,
}) {
  const overlay = document.getElementById('modal-confirmacion-global');
  if (!overlay) return;

  // Actualizar contenido
  overlay.querySelector('.modal-titulo').textContent    = titulo;
  overlay.querySelector('.modal-subtitulo').textContent = mensaje;

  const btnConfirmar = overlay.querySelector('[data-confirmar]');
  btnConfirmar.textContent = labelConfirmar;

  // Tipo visual
  const iconoEl = overlay.querySelector('.modal-icono');
  iconoEl.className = `modal-icono ${tipo}`;
  iconoEl.innerHTML = `<i data-lucide="${icono}" style="width:24px;height:24px;"></i>`;
  lucide.createIcons({ nodes: [iconoEl] });

  // Color del botón confirmar
  btnConfirmar.className = 'btn ' + (
    tipo === 'peligro' ? 'btn-peligro' :
    tipo === 'warning' ? 'btn-peligro' :
    'btn-primario'
  );
  btnConfirmar.setAttribute('data-confirmar', '');

  _modalCallback   = onConfirmar;
  _modalFormTarget = formId;

  abrirModal('modal-confirmacion-global');
}

// ─── Ejecutar confirmación ────────────────────────────────────────────────────
function _ejecutarConfirmacion() {
  if (_modalFormTarget) {
    const form = document.getElementById(_modalFormTarget);
    if (form) {
      cerrarModal('modal-confirmacion-global');
      form.submit();
      return;
    }
  }
  if (_modalCallback) {
    const callback = _modalCallback;  // ← Guardar referencia antes de cerrar
    cerrarModal('modal-confirmacion-global');
    callback();                       // ← Ejecutar después de cerrar
    return;
  }
  cerrarModal('modal-confirmacion-global');
}

// ─── Cerrar al hacer click fuera del modal ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', function(e) {
      if (e.target === this) {
        cerrarModal(this.id);
      }
    });
  });

  // Cerrar con Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.visible').forEach(overlay => {
        cerrarModal(overlay.id);
      });
    }
  });
});