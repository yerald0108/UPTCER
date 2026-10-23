/* ═══════════════════════════════════════════════════════════════════════════
   F43 — JS adaptado al formulario fiel (3 páginas Letter + catálogo equipos)
   ═══════════════════════════════════════════════════════════════════════════ */

let filaCount = 1;

/* URL base del endpoint de búsqueda de equipos (inyectada desde el template) */
function _urlBuscarEquipos() {
  return (window.F43_URLS && window.F43_URLS.buscarEquipos) || '/equipos/buscar/';
}

/* ─── Agregar fila ───────────────────────────────────────────────────────── */
function agregarFila() {
  filaCount++;
  const tbody = document.getElementById('equipos-tbody');
  if (!tbody) return;
  const fila = crearFila(filaCount);
  tbody.appendChild(fila);
  if (window.lucide) lucide.createIcons({ nodes: [fila] });
}

function crearFila(numero) {
  const tr = document.createElement('tr');
  tr.dataset.equipoId = '';
  tr.dataset.listado  = 'false';

  tr.innerHTML = `
    <td style="text-align:center;vertical-align:top;padding-top:10px;">${numero}</td>
    <td style="vertical-align:top;">
      <div style="position:relative;">
        <input type="text"
          class="f43-input-busqueda"
          placeholder="Busque en el catálogo o escriba manualmente..."
          autocomplete="off"
          oninput="buscarEnCatalogo(this)"
          onfocus="buscarEnCatalogo(this)">
        <div class="f43-dropdown" style="display:none;"></div>
      </div>
      <div class="f43-badge-no-listado" style="display:none;margin-top:3px;">
        <i data-lucide="alert-circle" style="width:11px;height:11px;"></i>
        Equipo no listado en catálogo
      </div>
      <div class="f43-badge-restringido" style="display:none;margin-top:3px;">
        <i data-lucide="shield-alert" style="width:11px;height:11px;"></i>
        Frecuencia restringida — requiere evaluación técnica
      </div>
      <div class="f43-badge-libre" style="display:none;margin-top:3px;">
        <i data-lucide="wifi" style="width:11px;height:11px;"></i>
        Banda libre (2.4 / 5.7 GHz)
      </div>
    </td>
    <td style="vertical-align:top;">
      <input type="text" class="f43-input-marca" placeholder="Marca">
    </td>
    <td style="vertical-align:top;">
      <input type="text" class="f43-input-modelo" placeholder="Modelo" style="font-family:var(--fuente-mono);font-size:9pt;">
    </td>
    <td style="vertical-align:top;">
      <input type="number" class="f43-input-cantidad" min="1" value="1" placeholder="1">
    </td>
    <td class="no-print" style="text-align:center;vertical-align:top;padding-top:8px;">
      <button type="button" onclick="eliminarFila(this)"
        style="background:none;border:none;cursor:pointer;color:#C62828;padding:2px;">
        <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
      </button>
    </td>
  `;

  return tr;
}

/* ─── Poblar equipos desde JSON (restauración tras error de validación) ──── */
function poblarEquiposDesdeJSON(equipos) {
  const tbody = document.getElementById('equipos-tbody');
  if (!tbody || !equipos.length) return;

  tbody.innerHTML = '';

  equipos.forEach((equipo, index) => {
    const numero = index + 1;
    const tr = document.createElement('tr');
    tr.dataset.equipoId = equipo.equipoId || '';
    tr.dataset.listado  = equipo.listado ? 'true' : 'false';

    tr.innerHTML = `
      <td style="text-align:center;vertical-align:top;padding-top:10px;">${numero}</td>
      <td style="vertical-align:top;">
        <div style="position:relative;">
          <input type="text"
            class="f43-input-busqueda"
            placeholder="Busque en el catálogo o escriba manualmente..."
            autocomplete="off"
            value="${escaparHTML(equipo.descripcion || '')}"
            oninput="buscarEnCatalogo(this)"
            onfocus="buscarEnCatalogo(this)">
          <div class="f43-dropdown" style="display:none;"></div>
        </div>
        <div class="f43-badge-no-listado" style="display:${!equipo.listado && equipo.descripcion ? 'flex' : 'none'};margin-top:3px;">
          <i data-lucide="alert-circle" style="width:11px;height:11px;"></i>
          Equipo no listado en catálogo
        </div>
        <div class="f43-badge-restringido" style="display:none;margin-top:3px;">
          <i data-lucide="shield-alert" style="width:11px;height:11px;"></i>
          Frecuencia restringida — requiere evaluación técnica
        </div>
        <div class="f43-badge-libre" style="display:none;margin-top:3px;">
          <i data-lucide="wifi" style="width:11px;height:11px;"></i>
          Banda libre (2.4 / 5.7 GHz)
        </div>
      </td>
      <td style="vertical-align:top;">
        <input type="text" class="f43-input-marca" placeholder="Marca" value="${escaparHTML(equipo.marca || '')}">
      </td>
      <td style="vertical-align:top;">
        <input type="text" class="f43-input-modelo" placeholder="Modelo" value="${escaparHTML(equipo.modelo || '')}" style="font-family:var(--fuente-mono);font-size:9pt;">
      </td>
      <td style="vertical-align:top;">
        <input type="number" class="f43-input-cantidad" min="1" value="${equipo.cantidad || 1}" placeholder="1">
      </td>
      <td class="no-print" style="text-align:center;vertical-align:top;padding-top:8px;">
        <button type="button" onclick="eliminarFila(this)"
          style="background:none;border:none;cursor:pointer;color:#C62828;padding:2px;">
          <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
        </button>
      </td>
    `;

    if (equipo.listado && equipo.equipoId) {
      const input = tr.querySelector('.f43-input-busqueda');
      input.style.borderBottom = '2px solid var(--color-secundario)';
      input.style.backgroundColor = '#F0FBF0';
      input.dataset.valorOriginal = equipo.descripcion;
    } else if (equipo.descripcion && !equipo.listado) {
      const input = tr.querySelector('.f43-input-busqueda');
      input.style.borderBottom = '2px solid var(--color-advertencia)';
      input.style.backgroundColor = '#FFFDF0';
    }

    tbody.appendChild(tr);
  });

  filaCount = equipos.length;
  if (window.lucide) lucide.createIcons({ nodes: [tbody] });
}

/* ─── Helper para escapar HTML ───────────────────────────────────────────── */
function escaparHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ─── Buscar en catálogo (AJAX) ──────────────────────────────────────────── */
let busquedaTimeout = null;
let abortController = null;

function buscarEnCatalogo(input) {
  const q        = input.value.trim();
  const fila     = input.closest('tr');
  const dropdown = input.nextElementSibling;
  const urlBase  = _urlBuscarEquipos();

  if (!dropdown) return;

  if (fila.dataset.equipoId && input.value === input.dataset.valorOriginal) return;

  if (fila.dataset.equipoId) {
    limpiarSeleccion(fila);
  }

  clearTimeout(busquedaTimeout);
  if (abortController) abortController.abort();

  if (q.length < 2) {
    if (q.length === 0) {
      clearTimeout(busquedaTimeout);
      if (abortController) abortController.abort();
      abortController = new AbortController();
      mostrarEstadoCargando(input, dropdown);
      fetch(`${urlBase}?q=`, { signal: abortController.signal })
        .then(r => r.json())
        .then(data => {
          quitarEstadoCargando(input);
          if (!data.equipos || data.equipos.length === 0) {
            dropdown.style.display = 'none';
            return;
          }
          dropdown.innerHTML = data.equipos.map(renderItemEquipo).join('');
          dropdown.style.display = 'block';
        })
        .catch(err => {
          if (err.name === 'AbortError') return;
          quitarEstadoCargando(input);
          dropdown.style.display = 'none';
        });
      return;
    }
    dropdown.style.display = 'none';
    quitarEstadoCargando(input);
    return;
  }

  mostrarEstadoCargando(input, dropdown);

  busquedaTimeout = setTimeout(() => {
    abortController = new AbortController();

    fetch(`${urlBase}?q=${encodeURIComponent(q)}`, {
      signal: abortController.signal
    })
      .then(r => r.json())
      .then(data => {
        quitarEstadoCargando(input);

        if (!data.equipos || data.equipos.length === 0) {
          dropdown.innerHTML = `
            <div class="f43-dropdown-vacio">
              <i data-lucide="search-x" style="width:14px;height:14px;opacity:0.5;"></i>
              No encontrado en catálogo — se registrará como equipo no listado
            </div>
          `;
          dropdown.style.display = 'block';
          if (window.lucide) lucide.createIcons({ nodes: [dropdown] });
          marcarNoListado(fila);
        } else {
          dropdown.innerHTML = data.equipos.map(renderItemEquipo).join('');
          dropdown.style.display = 'block';
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        quitarEstadoCargando(input);
        dropdown.style.display = 'none';
      });
  }, 300);
}

function renderItemEquipo(e) {
  return `
    <div class="f43-dropdown-item"
      onclick="seleccionarEquipo(this)"
      data-id="${e.id}"
      data-nombre="${e.nombre}"
      data-marca="${e.marca}"
      data-modelo="${e.modelo}"
      data-banda="${e.banda}"
      data-restringido="${e.restringido}"
      data-libre="${e.libre}">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div style="font-weight:600;font-size:10pt;">${e.marca} ${e.modelo}</div>
          <div style="font-size:9pt;color:#666;margin-top:1px;">${e.nombre}</div>
        </div>
        <div>
          ${e.restringido
            ? '<span style="font-size:8pt;background:#FFEBEE;color:#B71C1C;padding:2px 6px;border-radius:4px;border:1px solid #EF9A9A;">Restringida</span>'
            : e.libre
              ? '<span style="font-size:8pt;background:#E8F5E9;color:#1B5E20;padding:2px 6px;border-radius:4px;border:1px solid #A5D6A7;">Banda libre</span>'
              : '<span style="font-size:8pt;background:#E3F2FD;color:#0D47A1;padding:2px 6px;border-radius:4px;border:1px solid #90CAF9;">No aplica</span>'
          }
        </div>
      </div>
    </div>
  `;
}

function mostrarEstadoCargando(input, dropdown) {
  input.classList.add('f43-buscando');
  dropdown.innerHTML = `
    <div class="f43-dropdown-cargando">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" class="f43-spinner">
        <circle cx="9" cy="9" r="7" stroke="var(--color-borde)" stroke-width="2" opacity="0.3"/>
        <path d="M9 2a7 7 0 0 1 7 7" stroke="var(--color-primario)" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <span>Buscando en catálogo...</span>
    </div>
  `;
  dropdown.style.display = 'block';
}

function quitarEstadoCargando(input) {
  input.classList.remove('f43-buscando');
}

function seleccionarEquipo(item) {
  const fila     = item.closest('tr');
  const input    = fila.querySelector('.f43-input-busqueda');
  const dropdown = fila.querySelector('.f43-dropdown');

  const nombre      = item.dataset.nombre;
  const marca       = item.dataset.marca;
  const modelo      = item.dataset.modelo;
  const restringido = item.dataset.restringido === 'true';
  const libre       = item.dataset.libre === 'true';

  input.value = nombre;
  input.dataset.valorOriginal = nombre;
  fila.querySelector('.f43-input-marca').value  = marca;
  fila.querySelector('.f43-input-modelo').value = modelo;

  fila.dataset.equipoId = item.dataset.id;
  fila.dataset.listado  = 'true';

  dropdown.style.display = 'none';
  quitarEstadoCargando(input);

  ocultarBadges(fila);
  if (restringido) {
    fila.querySelector('.f43-badge-restringido').style.display = 'flex';
  } else if (libre) {
    fila.querySelector('.f43-badge-libre').style.display = 'flex';
  }

  input.style.borderBottom = '2px solid var(--color-secundario)';
  input.style.backgroundColor = '#F0FBF0';
}

function marcarNoListado(fila) {
  fila.dataset.equipoId = '';
  fila.dataset.listado  = 'false';

  ocultarBadges(fila);
  fila.querySelector('.f43-badge-no-listado').style.display = 'flex';

  const input = fila.querySelector('.f43-input-busqueda');
  input.style.borderBottom = '2px solid var(--color-advertencia)';
  input.style.backgroundColor = '#FFFDF0';
}

function limpiarSeleccion(fila) {
  fila.dataset.equipoId = '';
  fila.dataset.listado  = 'false';
  ocultarBadges(fila);

  const input = fila.querySelector('.f43-input-busqueda');
  input.style.borderBottom  = '';
  input.style.backgroundColor = '';
  input.dataset.valorOriginal = '';

  fila.querySelector('.f43-input-marca').value  = '';
  fila.querySelector('.f43-input-modelo').value = '';
}

function ocultarBadges(fila) {
  fila.querySelectorAll('.f43-badge-no-listado, .f43-badge-restringido, .f43-badge-libre')
    .forEach(b => b.style.display = 'none');
}

function eliminarFila(btn) {
  const filas = document.querySelectorAll('#equipos-tbody tr');
  if (filas.length <= 1) return;
  btn.closest('tr').remove();
  renumerarFilas();
}

function renumerarFilas() {
  document.querySelectorAll('#equipos-tbody tr').forEach((fila, i) => {
    fila.cells[0].textContent = i + 1;
  });
  filaCount = document.querySelectorAll('#equipos-tbody tr').length;
}

function recopilarEquipos() {
  const filas   = document.querySelectorAll('#equipos-tbody tr');
  const equipos = [];

  filas.forEach(fila => {
    const descripcion = fila.querySelector('.f43-input-busqueda')?.value.trim()  || '';
    const marca       = fila.querySelector('.f43-input-marca')?.value.trim()     || '';
    const modelo      = fila.querySelector('.f43-input-modelo')?.value.trim()    || '';
    const cantidad    = parseInt(fila.querySelector('.f43-input-cantidad')?.value) || 1;
    const equipoId    = fila.dataset.equipoId || '';
    const listado     = fila.dataset.listado === 'true';

    if (descripcion || marca || modelo) {
      equipos.push({ descripcion, marca, modelo, cantidad, equipoId, listado });
    }
  });

  return equipos;
}

function sincronizarEquiposJSON() {
  const json = document.getElementById('equipos-json');
  if (json) json.value = JSON.stringify(recopilarEquipos());
}

/* ═══════════════════════════════════════════════════════════════════════════
   CAMPOS CONDICIONALES
   ═══════════════════════════════════════════════════════════════════════════ */

(function initModoImportacion() {
  const hidden      = document.getElementById('modo_importacion_hidden');
  const chkEquipaje = document.getElementById('modo_equipaje');
  const chkRad      = document.getElementById('modo_rad');
  const chkCarga    = document.getElementById('modo_carga');
  if (!hidden) return;

  function sync() {
    if (chkRad?.checked) hidden.value = 'rad';
    else if (chkCarga?.checked) hidden.value = 'carga';
    else if (chkEquipaje?.checked) hidden.value = 'equipaje';
    else hidden.value = '';
  }

  function exclusivo(activo, otros) {
    otros.forEach(o => { if (o) o.checked = false; });
    if (activo) activo.checked = true;
    sync();
  }

  chkEquipaje?.addEventListener('change', () => exclusivo(chkEquipaje, [chkRad, chkCarga]));
  chkRad?.addEventListener('change',      () => exclusivo(chkRad,      [chkEquipaje, chkCarga]));
  chkCarga?.addEventListener('change',    () => exclusivo(chkCarga,    [chkEquipaje, chkRad]));

  sync();
})();

(function initObjetivo() {
  const hidden     = document.getElementById('objetivo_importacion_hidden');
  const chkEmpleo  = document.getElementById('obj_empleo');
  const chkMuestra = document.getElementById('obj_muestra');
  const chkOtros   = document.getElementById('obj_otros');
  if (!hidden) return;

  function sync() {
    if (chkOtros?.checked) hidden.value = 'otros';
    else if (chkMuestra?.checked) hidden.value = 'muestra_expositiva';
    else if (chkEmpleo?.checked) hidden.value = 'empleo_directo';
    else hidden.value = '';
  }

  function exclusivo(activo, otros) {
    otros.forEach(o => { if (o) o.checked = false; });
    if (activo) activo.checked = true;
    sync();
  }

  chkEmpleo?.addEventListener('change',  () => exclusivo(chkEmpleo,  [chkMuestra, chkOtros]));
  chkMuestra?.addEventListener('change', () => exclusivo(chkMuestra, [chkEmpleo, chkOtros]));
  chkOtros?.addEventListener('change',   () => {
    exclusivo(chkOtros, [chkEmpleo, chkMuestra]);
    toggleOtros(chkOtros.checked);
  });

  sync();
})();

function toggleOtros(checked) {
  const campo = document.getElementById('campo-otros');
  if (campo) campo.style.display = checked ? 'flex' : 'none';
}

function toggleRAD(checked) {
  const rad = document.getElementById('id_numero_rad');
  if (checked && rad) rad.focus();
}

function toggleTemporal(checked) {
  const input = document.getElementById('id_tiempo_solicitado');
  if (!input) return;
  input.disabled = !checked;
  if (!checked) input.value = '';
}

/* ═══════════════════════════════════════════════════════════════════════════
   PASAPORTE — 11 inputs sincronizados con hidden
   ═══════════════════════════════════════════════════════════════════════════ */
(function initPasaporte() {
  const grid   = document.getElementById('passport-grid');
  const hidden = document.getElementById('id_numero_pasaporte');
  if (!grid || !hidden) return;

  const inputs = Array.from(grid.querySelectorAll('input'));

  if (hidden.value) {
    const val = hidden.value.replace(/\s/g, '').toUpperCase();
    inputs.forEach((inp, i) => { inp.value = val[i] || ''; });
  }

  function syncHidden() {
    hidden.value = inputs.map(i => i.value).join('').trim();
  }

  inputs.forEach((inp, idx) => {
    inp.addEventListener('input', (e) => {
      e.target.value = e.target.value.replace(/[^A-Za-z0-9]/g, '').slice(0, 1).toUpperCase();
      if (e.target.value && idx < inputs.length - 1) {
        inputs[idx + 1].focus();
      }
      syncHidden();
    });

    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !inp.value && idx > 0) {
        inputs[idx - 1].focus();
      }
    });

    inp.addEventListener('paste', (e) => {
      e.preventDefault();
      const txt = (e.clipboardData || window.clipboardData).getData('text')
        .replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 11);
      txt.split('').forEach((ch, i) => { if (inputs[i]) inputs[i].value = ch; });
      syncHidden();
    });
  });

  const form = document.getElementById('form-f43');
  if (form) form.addEventListener('submit', syncHidden);
})();

/* ═══════════════════════════════════════════════════════════════════════════
   ENVIAR FORMULARIO
   ═══════════════════════════════════════════════════════════════════════════ */
function enviarFormulario() {
  const hiddenPass = document.getElementById('id_numero_pasaporte');
  const grid = document.getElementById('passport-grid');
  if (hiddenPass && grid) {
    hiddenPass.value = Array.from(grid.querySelectorAll('input')).map(i => i.value).join('').trim();
  }

  const equipos = recopilarEquipos();

  if (!document.getElementById('id_nombre_apellidos')?.value.trim()) {
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'warning', mensaje: 'Complete el nombre y apellidos del solicitante.' });
    } else {
      alert('Complete el nombre y apellidos del solicitante.');
    }
    document.getElementById('id_nombre_apellidos')?.focus();
    return;
  }
  if (!hiddenPass?.value.trim()) {
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'warning', mensaje: 'Complete el número de pasaporte.' });
    } else {
      alert('Complete el número de pasaporte.');
    }
    grid?.querySelector('input')?.focus();
    return;
  }
  if (!document.getElementById('id_provincia')?.value) {
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'warning', mensaje: 'Seleccione la provincia.' });
    } else {
      alert('Seleccione la provincia.');
    }
    return;
  }
  if (!document.getElementById('id_direccion_instalacion')?.value.trim()) {
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'warning', mensaje: 'Indique la dirección de utilización y ubíquela en el mapa.' });
    } else {
      alert('Indique la dirección de utilización y ubíquela en el mapa.');
    }
    document.getElementById('id_direccion_instalacion')?.focus();
    return;
  }
  if (
    !document.getElementById('id_latitud_instalacion')?.value ||
    !document.getElementById('id_longitud_instalacion')?.value
  ) {
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'warning', mensaje: 'Pulse «Ubicar dirección» antes de enviar la solicitud.' });
    } else {
      alert('Pulse «Ubicar dirección» antes de enviar la solicitud.');
    }
    document.getElementById('btn-ubicar-direccion')?.focus();
    return;
  }
  if (equipos.length === 0) {
    if (typeof mostrarToast === 'function') {
      mostrarToast({ tipo: 'warning', mensaje: 'Agregue al menos un equipo a la relación.' });
    } else {
      alert('Agregue al menos un equipo a la relación.');
    }
    return;
  }

  const restringidos = document.querySelectorAll('.f43-badge-restringido[style*="flex"]');
  if (restringidos.length > 0 && typeof mostrarToast === 'function') {
    mostrarToast({
      tipo:    'warning',
      titulo:  'Equipos con frecuencia restringida',
      mensaje: 'Su solicitud incluye equipos con frecuencia restringida. Será derivada al especialista técnico para evaluación.',
    });
  }

  const json = document.getElementById('equipos-json');
  if (json) json.value = JSON.stringify(equipos);

  try {
    localStorage.setItem('f43_equipos_respaldo', JSON.stringify(equipos));
  } catch(e) {}

  document.getElementById('form-f43')?.submit();
}

/* ═══════════════════════════════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  const temporal = document.getElementById('periodo_temporal');
  if (temporal) toggleTemporal(temporal.checked);

  const chkOtros = document.getElementById('obj_otros');
  if (chkOtros) toggleOtros(chkOtros.checked);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.f43-dropdown').forEach(d => d.style.display = 'none');
    }
  });

  document.addEventListener('click', function(e) {
    document.querySelectorAll('.f43-dropdown').forEach(dropdown => {
      const contenedor = dropdown.closest('td');
      if (contenedor && !contenedor.contains(e.target)) {
        dropdown.style.display = 'none';
      }
    });
  });

  document.addEventListener('focusin', function(e) {
    document.querySelectorAll('.f43-dropdown').forEach(dropdown => {
      const input = dropdown.previousElementSibling;
      if (input && input !== e.target) {
        dropdown.style.display = 'none';
      }
    });
  });

  window.addEventListener('scroll', function() {
    const btn = document.getElementById('btn-scroll-top');
    if (!btn) return;
    btn.classList.toggle('visible', window.scrollY > 400);
  });

  const jsonInput = document.getElementById('equipos-json');
  if (!jsonInput || !jsonInput.value || jsonInput.value === '[]') {
    localStorage.removeItem('f43_equipos_respaldo');
  }

  const MENSAJES = {
    'id_nombre_apellidos':     'El nombre y apellidos son obligatorios.',
    'id_pais_residencia':      'El país de residencia es obligatorio.',
    'id_direccion_residencia': 'La dirección de residencia es obligatoria.',
    'id_correo_electronico':   'El correo electrónico es obligatorio.',
    'id_telefono':             'El teléfono es obligatorio.',
    'id_provincia':            'Seleccione la provincia.',
  };

  function mostrarErrorCampo(campo, mensaje) {
    campo.style.borderBottom = '2px solid #C62828';
    campo.style.backgroundColor = '#FFF5F5';

    let errorEl = campo.parentElement.querySelector('.f43-error-inline');
    if (!errorEl) {
      errorEl = document.createElement('div');
      errorEl.className = 'f43-error-inline';
      errorEl.style.cssText = `
        font-size: 10px;
        color: #C62828;
        margin-top: 2px;
        display: flex;
        align-items: center;
        gap: 4px;
        font-family: var(--fuente-principal, Arial, sans-serif);
      `;
      campo.parentElement.appendChild(errorEl);
    }
    errorEl.textContent = mensaje;
  }

  function limpiarErrorCampo(campo) {
    campo.style.borderBottom = '';
    campo.style.backgroundColor = '';
    const errorEl = campo.parentElement.querySelector('.f43-error-inline');
    if (errorEl) errorEl.remove();
  }

  function validarCampoIndividual(campo) {
    const valor = (campo.value || '').trim();

    if (!valor) {
      mostrarErrorCampo(campo, MENSAJES[campo.id] || 'Este campo es obligatorio.');
      return false;
    }

    if (campo.type === 'email') {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(valor)) {
        mostrarErrorCampo(campo, 'Ingrese un correo electrónico válido.');
        return false;
      }
    }

    limpiarErrorCampo(campo);
    campo.style.borderBottom = '2px solid #2E7D32';
    campo.style.backgroundColor = '#F0FBF0';
    return true;
  }

  ['id_nombre_apellidos', 'id_pais_residencia', 'id_direccion_residencia',
   'id_correo_electronico', 'id_telefono'].forEach(id => {
    const campo = document.getElementById(id);
    if (!campo) return;

    campo.addEventListener('blur', () => {
      if (campo.value.trim()) validarCampoIndividual(campo);
    });

    campo.addEventListener('input', () => {
      if (campo.style.borderBottom.includes('C62828') && campo.value.trim()) {
        limpiarErrorCampo(campo);
      }
    });
  });

  const provincia = document.getElementById('id_provincia');
  if (provincia) {
    provincia.addEventListener('change', () => {
      if (provincia.value) {
        limpiarErrorCampo(provincia);
        provincia.style.borderBottom = '2px solid #2E7D32';
        provincia.style.backgroundColor = '#F0FBF0';
      } else {
        mostrarErrorCampo(provincia, 'Seleccione la provincia.');
      }
    });
  }
});