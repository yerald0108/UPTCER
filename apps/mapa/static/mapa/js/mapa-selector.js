import {
    anadirLimites,
    boundsFeature,
    buscarMunicipio,
    cargarLimites,
    crearMapa,
    maplibregl
} from './mapa-offline.js?v=3';

document.addEventListener('DOMContentLoaded', function () {
    var config = window.MAPA_SELECTOR_CONFIG || {};
    var estado = document.getElementById('selector-estado');
    var campoBusqueda = document.getElementById('busqueda-direccion');
    var botonBuscar = document.getElementById('btn-buscar');
    var botonConfirmar = document.getElementById('confirmar-ubicacion');
    var mapa = crearMapa('selector-mapa');
    var marcador = null;
    var seleccion = null;
    var limites = null;

    function actualizarSeleccion(latitud, longitud, direccion) {
        seleccion = { latitud: latitud, longitud: longitud, direccion: direccion || '' };
        if (marcador) marcador.remove();
        marcador = new maplibregl.Marker({ color: '#2563eb' })
            .setLngLat([longitud, latitud])
            .addTo(mapa);
        botonConfirmar.disabled = false;
        estado.textContent = direccion
            ? 'Punto seleccionado: ' + direccion
            : 'Punto seleccionado. Puede confirmar esta ubicación.';
    }

    function buscarLocal(texto) {
        var feature = buscarMunicipio(limites, texto);
        if (!feature) return false;
        mapa.fitBounds(boundsFeature(feature), { maxZoom: 12, padding: 24 });
        estado.textContent = 'Municipio localizado. Haga clic en el punto exacto antes de confirmar la ubicación.';
        return true;
    }

    async function buscarDireccion(texto) {
        var consulta = texto.trim();
        if (!consulta) {
            estado.textContent = 'Escriba una dirección, municipio o provincia.';
            campoBusqueda.focus();
            return;
        }
        if (buscarLocal(consulta)) return;

        botonBuscar.disabled = true;
        estado.textContent = 'Buscando dirección en línea…';
        try {
            var url = new URL('https://nominatim.openstreetmap.org/search');
            url.searchParams.set('format', 'jsonv2');
            url.searchParams.set('limit', '1');
            url.searchParams.set('q', consulta);
            var respuesta = await fetch(url.toString(), { headers: { Accept: 'application/json' } });
            if (!respuesta.ok) throw new Error('No se pudo consultar la búsqueda de direcciones.');
            var resultados = await respuesta.json();
            if (!resultados.length) throw new Error('No se encontró la dirección. Pruebe con más detalles.');

            var resultado = resultados[0];
            var latitud = Number(resultado.lat);
            var longitud = Number(resultado.lon);
            mapa.flyTo({ center: [longitud, latitud], zoom: 14 });
            actualizarSeleccion(latitud, longitud, resultado.display_name || consulta);
        } catch (error) {
            estado.textContent = (error.message || 'No se encontró la dirección.') +
                ' También puede marcar el punto directamente en el mapa.';
        } finally {
            botonBuscar.disabled = false;
        }
    }

    document.getElementById('form-busqueda').addEventListener('submit', function (evento) {
        evento.preventDefault();
        buscarDireccion(campoBusqueda.value);
    });

    mapa.on('click', function (evento) {
        actualizarSeleccion(evento.lngLat.lat, evento.lngLat.lng, '');
        var coordenadas = evento.lngLat;
        var url = new URL('https://nominatim.openstreetmap.org/reverse');
        url.searchParams.set('format', 'jsonv2');
        url.searchParams.set('lat', coordenadas.lat);
        url.searchParams.set('lon', coordenadas.lng);
        fetch(url.toString(), { headers: { Accept: 'application/json' } })
            .then(function (respuesta) {
                if (!respuesta.ok) throw new Error('No se pudo obtener la dirección.');
                return respuesta.json();
            })
            .then(function (resultado) {
                if (!seleccion || seleccion.latitud !== coordenadas.lat) return;
                seleccion.direccion = resultado.display_name || '';
                campoBusqueda.value = seleccion.direccion;
                estado.textContent = seleccion.direccion
                    ? 'Punto seleccionado: ' + seleccion.direccion
                    : 'Punto seleccionado. Puede confirmar esta ubicación.';
            })
            .catch(function () {
                estado.textContent = 'Punto seleccionado. La dirección automática requiere Internet.';
            });
    });

    botonConfirmar.addEventListener('click', function () {
        if (!seleccion) return;
        if (!window.opener || window.opener.closed) {
            estado.textContent = 'Vuelva al formulario y abra el selector desde el botón de ubicación.';
            return;
        }
        window.opener.postMessage({
            tipo: 'uptcer-ubicacion-seleccionada',
            latitud: seleccion.latitud,
            longitud: seleccion.longitud,
            direccion: seleccion.direccion
        }, window.location.origin);
        window.close();
    });

    document.getElementById('cerrar-selector').addEventListener('click', function () {
        window.close();
    });

    mapa.on('load', function () {
        cargarLimites().then(function (datos) {
            limites = datos;
            anadirLimites(mapa, limites);
            if (Number.isFinite(config.lat) && Number.isFinite(config.lon)) {
                mapa.setCenter([config.lon, config.lat]);
                mapa.setZoom(14);
                actualizarSeleccion(config.lat, config.lon, campoBusqueda.value);
            } else if (campoBusqueda.value.trim()) {
                buscarDireccion(campoBusqueda.value);
            } else {
                mapa.fitBounds([[-85.2, 19.7], [-74.1, 23.4]], { padding: 24 });
            }
        }).catch(function (error) {
            estado.textContent = error.message;
        });
    });
});
