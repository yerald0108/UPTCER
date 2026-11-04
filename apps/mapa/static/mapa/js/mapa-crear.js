import { anadirLimites, cargarLimites, crearMapa, maplibregl } from './mapa-offline.js?v=3';

document.addEventListener('DOMContentLoaded', function () {
    var config = window.MAPA_CREAR_CONFIG || {};
    var campoLatitud = document.getElementById('latitud');
    var campoLongitud = document.getElementById('longitud');
    var marker = null;
    var latitudInicial = Number(campoLatitud.value);
    var longitudInicial = Number(campoLongitud.value);
    var centro = Number.isFinite(latitudInicial) && Number.isFinite(longitudInicial)
        ? [longitudInicial, latitudInicial]
        : [-79, 22];
    var mapa = crearMapa('mini-mapa', centro, campoLatitud.value && campoLongitud.value ? 14 : 6);

    function actualizarMarcador(longitud, latitud) {
        if (marker) marker.remove();
        marker = new maplibregl.Marker({ color: '#2563eb' })
            .setLngLat([longitud, latitud])
            .addTo(mapa);
    }

    mapa.on('load', function () {
        cargarLimites().then(function (limites) {
            anadirLimites(mapa, limites);
            if (campoLatitud.value && campoLongitud.value) {
                actualizarMarcador(Number(campoLongitud.value), Number(campoLatitud.value));
            } else {
                mapa.fitBounds([[-85.2, 19.7], [-74.1, 23.4]], { padding: 24 });
            }
        }).catch(function (error) {
            mostrarMensaje(error.message, 'danger');
        });
    });

    mapa.on('click', function (evento) {
        campoLatitud.value = evento.lngLat.lat.toFixed(6);
        campoLongitud.value = evento.lngLat.lng.toFixed(6);
        actualizarMarcador(evento.lngLat.lng, evento.lngLat.lat);
    });

    [campoLatitud, campoLongitud].forEach(function (campo) {
        campo.addEventListener('change', function () {
            var latitud = Number(campoLatitud.value);
            var longitud = Number(campoLongitud.value);
            if (!Number.isFinite(latitud) || !Number.isFinite(longitud)) return;
            actualizarMarcador(longitud, latitud);
            mapa.setCenter([longitud, latitud]);
            mapa.setZoom(14);
        });
    });

    function mostrarMensaje(texto, tipo) {
        var mensaje = document.getElementById('mensaje');
        mensaje.replaceChildren();
        var aviso = document.createElement('div');
        aviso.className = 'alert alert-' + tipo;
        aviso.textContent = texto;
        mensaje.appendChild(aviso);
    }

    document.getElementById('form-crear-punto').addEventListener('submit', function (evento) {
        evento.preventDefault();
        var formulario = evento.currentTarget;
        var atributos = {};
        var atributosTexto = formulario.querySelector('[name="atributos"]').value.trim();
        if (atributosTexto) {
            try {
                atributos = JSON.parse(atributosTexto);
            } catch (error) {
                mostrarMensaje('El JSON de atributos no es válido.', 'danger');
                return;
            }
            if (!atributos || typeof atributos !== 'object' || Array.isArray(atributos)) {
                mostrarMensaje('Los atributos deben ser un objeto JSON.', 'danger');
                return;
            }
        }

        ['frecuencia_mhz', 'radio_km'].forEach(function (campo) {
            var valor = formulario.elements[campo].value;
            if (valor !== '') atributos[campo] = Number(valor);
        });

        fetch(config.apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': formulario.querySelector('[name="csrfmiddlewaretoken"]').value
            },
            body: JSON.stringify({
                nombre: formulario.elements.nombre.value,
                tipo: formulario.elements.tipo.value,
                latitud: campoLatitud.value,
                longitud: campoLongitud.value,
                estado: formulario.elements.estado.value,
                responsable: formulario.elements.responsable.value,
                descripcion: formulario.elements.descripcion.value,
                atributos: atributos
            })
        })
            .then(function (respuesta) {
                return respuesta.json().then(function (datos) {
                    if (!respuesta.ok) throw new Error(datos.error || 'No se pudo guardar el punto.');
                    return datos;
                });
            })
            .then(function (datos) {
                mostrarMensaje(datos.mensaje, 'success');
                window.setTimeout(function () { window.location.href = config.urlMapa; }, 1200);
            })
            .catch(function (error) {
                mostrarMensaje(error.message || 'Error al guardar el punto.', 'danger');
            });
    });
});
