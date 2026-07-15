/* ─── Formulario F43 — equipos con búsqueda en catálogo ─────────────────── */

let filaCount = 1;

// ─── Agregar fila ─────────────────────────────────────────────────────────────
function agregarFila() {
  filaCount++;
  const tbody = document.getElementById('equipos-tbody');
  const fila  = crearFila(filaCount);
  tbody.appendChild(fila);
  lucide.createIcons({ nodes: [fila] });
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

  // Cerrar dropdown al hacer click fuera
  document.addEventListener('click', function(e) {
    const dropdowns = document.querySelectorAll('.f43-dropdown');
    dropdowns.forEach(d => {
      if (!d.parentElement.contains(e.target)) {
        d.style.display = 'none';
      }
    });
  });

  return tr;
}

// ─── Poblar equipos desde JSON (restauración tras error de validación) ─────
function poblarEquiposDesdeJSON(equipos) {
  const tbody = document.getElementById('equipos-tbody');
  if (!tbody || !equipos.length) return;

  // Limpiar tabla existente
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

    // Si es equipo del catálogo, poner estilos de seleccionado
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

  // Re-inicializar iconos Lucide
  lucide.createIcons({ nodes: [tbody] });
}

// ─── Helper para escapar HTML ────────────────────────────────────────────────
function escaparHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ─── Buscar en catálogo (AJAX) ────────────────────────────────────────────────
let busquedaTimeout = null;
let abortController = null;  // Para cancelar peticiones anteriores

function buscarEnCatalogo(input) {
  const q        = input.value.trim();
  const fila     = input.closest('tr');
  const dropdown = input.nextElementSibling;

  // Si ya tiene un equipo del catálogo seleccionado y no cambió el texto, no buscar
  if (fila.dataset.equipoId && input.value === input.dataset.valorOriginal) return;

  // Limpiar selección previa si el usuario edita el texto
  if (fila.dataset.equipoId) {
    limpiarSeleccion(fila);
  }

  clearTimeout(busquedaTimeout);

  // Cancelar petición anterior si existe
  if (abortController) {
    abortController.abort();
  }

  if (q.length < 2) {
    dropdown.style.display = 'none';
    quitarEstadoCargando(input);
    return;
  }

  // ─── Mostrar estado de carga ──────────────────────────────────────────
  mostrarEstadoCargando(input, dropdown);

  busquedaTimeout = setTimeout(() => {
    abortController = new AbortController();

    fetch(`/equipos/buscar/?q=${encodeURIComponent(q)}`, {
      signal: abortController.signal
    })
      .then(r => r.json())
      .then(data => {
        // Quitar estado de carga
        quitarEstadoCargando(input);

        if (data.equipos.length === 0) {
          dropdown.innerHTML = `
            <div class="f43-dropdown-vacio">
              <i data-lucide="search-x" style="width:14px;height:14px;opacity:0.5;"></i>
              No encontrado en catálogo — se registrará como equipo no listado
            </div>
          `;
          dropdown.style.display = 'block';
          lucide.createIcons({ nodes: [dropdown] });

          // Marcar como no listado
          marcarNoListado(fila);
        } else {
          dropdown.innerHTML = data.equipos.map(e => `
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
          `).join('');
          dropdown.style.display = 'block';
        }
      })
      .catch((err) => {
        // Ignorar errores por abort
        if (err.name === 'AbortError') return;
        quitarEstadoCargando(input);
        dropdown.style.display = 'none';
      });
  }, 300);
}

// ─── Estado de carga ──────────────────────────────────────────────────────────
function mostrarEstadoCargando(input, dropdown) {
  // Clase visual en el input
  input.classList.add('f43-buscando');

  // Mostrar spinner en el dropdown
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

// ─── Seleccionar equipo del catálogo ─────────────────────────────────────────
function seleccionarEquipo(item) {
  const fila     = item.closest('tr');
  const input    = fila.querySelector('.f43-input-busqueda');
  const dropdown = fila.querySelector('.f43-dropdown');

  const nombre      = item.dataset.nombre;
  const marca       = item.dataset.marca;
  const modelo      = item.dataset.modelo;
  const restringido = item.dataset.restringido === 'true';
  const libre       = item.dataset.libre === 'true';

  // Rellenar campos
  input.value = nombre;
  input.dataset.valorOriginal = nombre;
  fila.querySelector('.f43-input-marca').value  = marca;
  fila.querySelector('.f43-input-modelo').value = modelo;

  // Guardar ID del equipo
  fila.dataset.equipoId = item.dataset.id;
  fila.dataset.listado  = 'true';

  // Ocultar dropdown
  dropdown.style.display = 'none';

  // Quitar estado de carga
  quitarEstadoCargando(input);

  // Mostrar badge de banda
  ocultarBadges(fila);
  if (restringido) {
    fila.querySelector('.f43-badge-restringido').style.display = 'flex';
  } else if (libre) {
    fila.querySelector('.f43-badge-libre').style.display = 'flex';
  }

  // Estilo visual de campo seleccionado
  input.style.borderBottom = '2px solid var(--color-secundario)';
  input.style.backgroundColor = '#F0FBF0';
}

// ─── Marcar como no listado ───────────────────────────────────────────────────
function marcarNoListado(fila) {
  fila.dataset.equipoId = '';
  fila.dataset.listado  = 'false';

  ocultarBadges(fila);
  fila.querySelector('.f43-badge-no-listado').style.display = 'flex';

  const input = fila.querySelector('.f43-input-busqueda');
  input.style.borderBottom = '2px solid var(--color-advertencia)';
  input.style.backgroundColor = '#FFFDF0';
}

// ─── Limpiar selección ────────────────────────────────────────────────────────
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

// ─── Eliminar fila ────────────────────────────────────────────────────────────
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

// ─── Recopilar equipos para envío ────────────────────────────────────────────
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

// ─── Campos condicionales ─────────────────────────────────────────────────────
function toggleRAD(checked) {
  document.getElementById('modo_importacion_hidden').value = checked ? 'rad' : 'equipaje';
}

function toggleOtros(checked) {
  document.getElementById('campo-otros').style.display = checked ? 'block' : 'none';
  const hidden = document.getElementById('objetivo_importacion_hidden');
  hidden.value = checked ? 'otros' : 'empleo_directo';
}

function toggleTemporal(checked) {
  const input = document.getElementById('id_tiempo_solicitado');
  input.disabled = !checked;
  if (!checked) input.value = '';
}

document.querySelectorAll('input[name="periodo_importacion"]').forEach(r => {
  r.addEventListener('change', function() {
    toggleTemporal(this.value === 'temporal');
  });
});

// ─── Manejo de archivo adjunto ────────────────────────────────────────────────
function mostrarArchivo(input) {
  if (input.files && input.files[0]) {
    const archivo = input.files[0];
    document.getElementById('upload-area').style.display          = 'none';
    document.getElementById('archivo-seleccionado').style.display = 'flex';
    document.getElementById('nombre-archivo').textContent          = archivo.name;
  }
}

function quitarArchivo() {
  document.getElementById('id_documento_adjunto').value            = '';
  document.getElementById('upload-area').style.display             = 'flex';
  document.getElementById('archivo-seleccionado').style.display    = 'none';
}

// ─── Enviar formulario ────────────────────────────────────────────────────────
function enviarFormulario() {
  const equipos = recopilarEquipos();

  if (!document.getElementById('id_nombre_apellidos').value.trim()) {
    mostrarToast({ tipo: 'warning', mensaje: 'Complete el nombre y apellidos del solicitante.' });
    document.getElementById('id_nombre_apellidos').focus();
    return;
  }
  if (!document.getElementById('id_numero_pasaporte').value.trim()) {
    mostrarToast({ tipo: 'warning', mensaje: 'Complete el número de pasaporte.' });
    document.getElementById('id_numero_pasaporte').focus();
    return;
  }
  if (!document.getElementById('id_provincia').value) {
    mostrarToast({ tipo: 'warning', mensaje: 'Seleccione la provincia.' });
    return;
  }
  if (equipos.length === 0) {
    mostrarToast({ tipo: 'warning', mensaje: 'Agregue al menos un equipo a la relación.' });
    return;
  }

  // Advertir si hay equipos con frecuencia restringida
  const restringidos = document.querySelectorAll('.f43-badge-restringido[style*="flex"]');
  if (restringidos.length > 0) {
    mostrarToast({
      tipo:    'warning',
      titulo:  'Equipos con frecuencia restringida',
      mensaje: 'Su solicitud incluye equipos con frecuencia restringida. Será derivada al especialista técnico para evaluación.',
    });
  }

  document.getElementById('equipos-json').value = JSON.stringify(equipos);

  // Guardar en localStorage como respaldo extra
  try {
    localStorage.setItem('f43_equipos_respaldo', JSON.stringify(equipos));
  } catch(e) {
    // Silencioso si localStorage está lleno
  }

  document.getElementById('form-f43').submit();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();

  // Cerrar dropdowns con Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.f43-dropdown').forEach(d => d.style.display = 'none');
    }
  });

  // Limpiar respaldo de localStorage si estamos en una carga limpia (sin error previo)
  if (!document.getElementById('equipos-json').value || document.getElementById('equipos-json').value === '[]') {
    localStorage.removeItem('f43_equipos_respaldo');
  }

  // ── Validación en tiempo real (on blur) ──────────────────────────────────

  const MENSAJES = {
    'id_nombre_apellidos':    'El nombre y apellidos son obligatorios.',
    'id_numero_pasaporte':    'El número de pasaporte es obligatorio.',
    'id_pais_residencia':     'El país de residencia es obligatorio.',
    'id_direccion_residencia':'La dirección de residencia es obligatoria.',
    'id_correo_electronico':  'El correo electrónico es obligatorio.',
    'id_telefono':            'El teléfono es obligatorio.',
    'id_provincia':           'Seleccione la provincia.',
  };

  function mostrarErrorCampo(campo, mensaje) {
    campo.style.borderBottom = '2px solid #C62828';
    campo.style.backgroundColor = '#FFF5F5';

    let errorEl = campo.parentElement.querySelector('.f43-error-inline');
    if (!errorEl) {
      errorEl = document.createElement('div');
      errorEl.className = 'f43-error-inline';
      errorEl.style.cssText = `
        font-size: 11px;
        color: #C62828;
        margin-top: 3px;
        display: flex;
        align-items: center;
        gap: 4px;
        font-family: var(--fuente-principal);
      `;
      campo.parentElement.appendChild(errorEl);
    }
    errorEl.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      ${mensaje}
    `;
  }

  function limpiarErrorCampo(campo) {
    campo.style.borderBottom = '';
    campo.style.backgroundColor = '';
    const errorEl = campo.parentElement.querySelector('.f43-error-inline');
    if (errorEl) errorEl.remove();
  }

  function validarCampoIndividual(campo) {
    const valor = campo.value.trim();

    if (!valor) {
      const mensaje = MENSAJES[campo.id] || 'Este campo es obligatorio.';
      mostrarErrorCampo(campo, mensaje);
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

  const camposValidar = [
    'id_nombre_apellidos',
    'id_numero_pasaporte',
    'id_pais_residencia',
    'id_direccion_residencia',
    'id_correo_electronico',
    'id_telefono',
  ];

  camposValidar.forEach(id => {
    const campo = document.getElementById(id);
    if (!campo) return;

    campo.addEventListener('blur', () => {
      if (campo.value.trim()) {
        validarCampoIndividual(campo);
      }
    });

    campo.addEventListener('input', () => {
      if (campo.style.borderBottom.includes('C62828')) {
        if (campo.value.trim()) {
          limpiarErrorCampo(campo);
        }
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

  const btnContinuarPaso1 = document.querySelector('#paso-1 .tarjeta-pie .btn-primario');
  if (btnContinuarPaso1) {
    btnContinuarPaso1.addEventListener('click', (e) => {
      e.stopPropagation();
      let todoValido = true;
      camposValidar.forEach(id => {
        const campo = document.getElementById(id);
        if (campo && !validarCampoIndividual(campo)) {
          todoValido = false;
        }
      });
      if (!todoValido) {
        mostrarToast({
          tipo:    'warning',
          titulo:  'Campos incompletos',
          mensaje: 'Complete todos los campos requeridos antes de continuar.',
        });
        const primerError = document.querySelector('.f43-error-inline');
        if (primerError) {
          primerError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }, true);
  }
  
});