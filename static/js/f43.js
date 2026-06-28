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

// ─── Buscar en catálogo (AJAX) ────────────────────────────────────────────────
let busquedaTimeout = null;

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

  if (q.length < 2) {
    dropdown.style.display = 'none';
    return;
  }

  busquedaTimeout = setTimeout(() => {
    fetch(`/equipos/buscar/?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => {
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
      .catch(() => {
        dropdown.style.display = 'none';
      });
  }, 300);
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
  document.getElementById('form-f43').submit();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // La primera fila ya está en el HTML — inicializar eventos
  lucide.createIcons();

  // Cerrar dropdowns con Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.f43-dropdown').forEach(d => d.style.display = 'none');
    }
  });
});