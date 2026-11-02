import {
    anadirLimites,
    boundsFeature,
    cargarLimites,
    crearCobertura,
    crearMapa,
    maplibregl,
    municipioDePunto,
    obtenerNombres
} from './mapa-offline.js?v=3';

document.addEventListener('DOMContentLoaded', function () {
    var config = window.MAPA_DIRECTIVO_CONFIG;
    if (!config) return;

    var mapa = crearMapa('mapa-directivo');
    var puntos = [];
    var limites = null;
    var estado = document.getElementById('mapa-directivo-estado');
    var filtroProvincia = document.getElementById('mapa-provincia');
    var filtroMunicipio = document.getElementById('mapa-municipio');
    var filtroDesde = document.getElementById('mapa-frecuencia-desde');
    var filtroHasta = document.getElementById('mapa-frecuencia-hasta');
    var total = document.getElementById('mapa-directivo-total');
    var solapamientos = document.getElementById('mapa-directivo-solapamientos');
    var mostrarSatelites = document.getElementById('mapa-mostrar-satelites');
    var filtroSatelite = document.getElementById('mapa-filtro-satelite');
    var estadoSatelites = document.getElementById('mapa-satelites-estado');
    var intervaloSatelites = null;
    var datosSatelites = null;

    function numeroFrecuencia(properties) {
        var candidatos = [
            properties.frecuencia_mhz,
            properties.frecuencia,
            properties.frequency_mhz,
            properties.frequency
        ];
        if (Array.isArray(properties.equipos)) {
            properties.equipos.forEach(function (equipo) {
                if (!equipo || typeof equipo !== 'object') return;
                candidatos.push(equipo.frecuencia_mhz, equipo.frecuencia, equipo.frequency_mhz);
            });
        }
        for (var i = 0; i < candidatos.length; i++) {
            var coincidencia = String(candidatos[i] || '').replace(',', '.').match(/-?\d+(?:\.\d+)?/);
            var numero = coincidencia ? Number(coincidencia[0]) : NaN;
            if (Number.isFinite(numero) && numero > 0) return numero;
        }
        return null;
    }

    function radioCobertura(properties) {
        var radio = Number(properties.radio_km);
        return Number.isFinite(radio) && radio > 0 && radio <= 1000 ? radio : null;
    }

    function colorFrecuencia(frecuencia) {
        if (frecuencia === null) return '#64748b';
        var colores = ['#2563eb', '#7c3aed', '#0891b2', '#059669', '#d97706', '#db2777'];
        return colores[Math.abs(Math.round(frecuencia * 10)) % colores.length];
    }

    function actualizarMunicipios() {
        var provincia = filtroProvincia.value;
        var municipioActual = filtroMunicipio.value;
        var municipios = {};
        limites.features.forEach(function (feature) {
            var properties = feature.properties || {};
            if (properties.municipality && (!provincia || properties.province === provincia)) {
                municipios[properties.municipality] = true;
            }
        });
        filtroMunicipio.replaceChildren(new Option('Todos los municipios', ''));
        Object.keys(municipios)
            .sort(function (a, b) { return a.localeCompare(b, 'es'); })
            .forEach(function (nombre) {
                filtroMunicipio.add(new Option(nombre, nombre));
            });
        if (municipios[municipioActual]) filtroMunicipio.value = municipioActual;
    }

    function distanciaKm(puntoA, puntoB) {
        var latA = puntoA[1] * Math.PI / 180;
        var latB = puntoB[1] * Math.PI / 180;
        var deltaLatitud = latB - latA;
        var deltaLongitud = (puntoB[0] - puntoA[0]) * Math.PI / 180;
        var haversine = Math.sin(deltaLatitud / 2) ** 2 +
            Math.cos(latA) * Math.cos(latB) * Math.sin(deltaLongitud / 2) ** 2;
        return 6371.0088 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
    }

    function obtenerFiltros() {
        return {
            desde: filtroDesde.value === '' ? null : Number(filtroDesde.value),
            hasta: filtroHasta.value === '' ? null : Number(filtroHasta.value)
        };
    }

    function actualizarMapa() {
        if (!mapa.getSource('puntos-directivo') || !mapa.getSource('cobertura-directivo')) return;
        var filtros = obtenerFiltros();
        solapamientos.replaceChildren();
        if (filtros.desde !== null && filtros.hasta !== null && filtros.desde > filtros.hasta) {
            total.textContent = '0';
            estado.textContent = 'La frecuencia inicial debe ser menor o igual que la frecuencia final.';
            mapa.getSource('puntos-directivo').setData({ type: 'FeatureCollection', features: [] });
            mapa.getSource('cobertura-directivo').setData({ type: 'FeatureCollection', features: [] });
            return;
        }

        var visibles = puntos.filter(function (punto) {
            var propiedades = punto.properties;
            var frecuenciaCoincide = punto.frecuencia !== null &&
                (filtros.desde === null || punto.frecuencia >= filtros.desde) &&
                (filtros.hasta === null || punto.frecuencia <= filtros.hasta);
            var frecuenciaSinFiltrar = filtros.desde === null && filtros.hasta === null;
            return (!filtroProvincia.value || propiedades.provincia === filtroProvincia.value) &&
                (!filtroMunicipio.value || propiedades.municipio === filtroMunicipio.value) &&
                (frecuenciaSinFiltrar || frecuenciaCoincide);
        });
        var conRadio = visibles.filter(function (punto) { return punto.radio !== null; });
        var solapaPorId = {};

        for (var i = 0; i < conRadio.length; i++) {
            for (var j = i + 1; j < conRadio.length; j++) {
                if (distanciaKm(conRadio[i].coordinates, conRadio[j].coordinates) <
                    conRadio[i].radio + conRadio[j].radio) {
                    solapaPorId[conRadio[i].properties.id] = conRadio[j];
                    solapaPorId[conRadio[j].properties.id] = conRadio[i];
                }
            }
        }

        var puntosVisibles = visibles.map(function (punto) {
            var propiedades = Object.assign({}, punto.properties);
            propiedades.solapa = Boolean(solapaPorId[propiedades.id]);
            propiedades.color = solapaPorId[propiedades.id]
                ? '#dc2626'
                : colorFrecuencia(punto.frecuencia);
            return {
                type: 'Feature',
                geometry: { type: 'Point', coordinates: punto.coordinates },
                properties: propiedades
            };
        });
        var coberturas = conRadio.map(function (punto) {
            var solapa = Boolean(solapaPorId[punto.properties.id]);
            return crearCobertura(
                punto.coordinates[0],
                punto.coordinates[1],
                punto.radio,
                {
                    id: punto.properties.id,
                    color: solapa ? '#dc2626' : colorFrecuencia(punto.frecuencia),
                    solapa: solapa
                }
            );
        });

        mapa.getSource('puntos-directivo').setData({
            type: 'FeatureCollection',
            features: puntosVisibles
        });
        mapa.getSource('cobertura-directivo').setData({
            type: 'FeatureCollection',
            features: coberturas
        });

        Object.keys(solapaPorId).forEach(function (id) {
            var punto = puntos.find(function (item) { return String(item.properties.id) === id; });
            var otro = solapaPorId[id];
            if (!punto || Number(id) > Number(otro.properties.id)) return;
            var item = document.createElement('li');
            item.textContent = punto.properties.nombre + ' solapa con ' + otro.properties.nombre;
            solapamientos.appendChild(item);
        });
        total.textContent = visibles.length;
        estado.textContent = visibles.length
            ? visibles.length + ' punto(s). Los círculos son radios manuales estimados; el rojo indica solapamiento geométrico.'
            : 'No hay puntos que coincidan con los filtros seleccionados.';
    }

    function anadirCapasPuntos() {
        mapa.addSource('cobertura-directivo', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });
        mapa.addLayer({
            id: 'cobertura-directivo-fill',
            type: 'fill',
            source: 'cobertura-directivo',
            paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.15 }
        });
        mapa.addLayer({
            id: 'cobertura-directivo-line',
            type: 'line',
            source: 'cobertura-directivo',
            paint: { 'line-color': ['get', 'color'], 'line-width': 2 }
        });
        mapa.addSource('puntos-directivo', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });
        mapa.addLayer({
            id: 'puntos-directivo-circulos',
            type: 'circle',
            source: 'puntos-directivo',
            paint: {
                'circle-radius': 7,
                'circle-color': ['get', 'color'],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff'
            }
        });
        mapa.on('click', 'puntos-directivo-circulos', function (evento) {
            var feature = evento.features && evento.features[0];
            if (!feature) return;
            var properties = feature.properties || {};
            var contenido = document.createElement('div');
            var titulo = document.createElement('strong');
            titulo.textContent = properties.nombre || 'Punto sin nombre';
            contenido.appendChild(titulo);
            [
                ['Provincia', properties.provincia],
                ['Municipio', properties.municipio],
                ['Frecuencia', properties.frecuencia_mhz ? properties.frecuencia_mhz + ' MHz' : 'No informada'],
                ['Radio estimado', properties.radio_km ? properties.radio_km + ' km' : 'No informado'],
                ['Solapamiento', properties.solapa ? 'Sí' : 'No detectado']
            ].forEach(function (fila) {
                var linea = document.createElement('div');
                linea.textContent = fila[0] + ': ' + (fila[1] || 'Sin identificar');
                contenido.appendChild(linea);
            });
            new maplibregl.Popup()
                .setLngLat(evento.lngLat)
                .setDOMContent(contenido)
                .addTo(mapa);
        });
        mapa.on('mouseenter', 'puntos-directivo-circulos', function () {
            mapa.getCanvas().style.cursor = 'pointer';
        });
        mapa.on('mouseleave', 'puntos-directivo-circulos', function () {
            mapa.getCanvas().style.cursor = '';
        });
    }

    function anadirCapasSatelites() {
        mapa.addSource('trayectorias-satelitales', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });
        mapa.addLayer({
            id: 'huellas-satelitales',
            type: 'fill',
            source: 'trayectorias-satelitales',
            filter: ['==', ['get', 'tipo'], 'huella'],
            paint: { 'fill-color': '#fbbf24', 'fill-opacity': 0.025 }
        }, 'limites-cuba-line');
        mapa.addLayer({
            id: 'trayectorias-satelitales-lineas',
            type: 'line',
            source: 'trayectorias-satelitales',
            filter: ['==', ['get', 'tipo'], 'trayectoria'],
            paint: {
                'line-color': '#c2410c',
                'line-width': 1.5,
                'line-opacity': 0.65
            }
        }, 'limites-cuba-line');
        mapa.addLayer({
            id: 'huellas-satelitales-borde',
            type: 'line',
            source: 'trayectorias-satelitales',
            filter: ['==', ['get', 'tipo'], 'huella'],
            paint: {
                'line-color': '#d97706',
                'line-width': 0.6,
                'line-opacity': 0.3
            }
        }, 'limites-cuba-line');
        mapa.addLayer({
            id: 'trayectorias-satelitales-posiciones',
            type: 'circle',
            source: 'trayectorias-satelitales',
            filter: ['==', ['get', 'tipo'], 'posicion'],
            paint: {
                'circle-radius': 5,
                'circle-color': '#ea580c',
                'circle-stroke-width': 1.5,
                'circle-stroke-color': '#ffffff'
            }
        });
        mapa.on('click', 'trayectorias-satelitales-posiciones', function (evento) {
            var feature = evento.features && evento.features[0];
            if (!feature) return;
            var properties = feature.properties || {};
            var contenido = document.createElement('div');
            var titulo = document.createElement('strong');
            titulo.textContent = properties.nombre || 'Satélite activo';
            contenido.appendChild(titulo);
            var identificador = document.createElement('div');
            identificador.textContent = 'NORAD: ' + properties.norad_id;
            contenido.appendChild(identificador);
            new maplibregl.Popup()
                .setLngLat(evento.lngLat)
                .setDOMContent(contenido)
                .addTo(mapa);
        });
        mapa.on('mouseenter', 'trayectorias-satelitales-posiciones', function () {
            mapa.getCanvas().style.cursor = 'pointer';
        });
        mapa.on('mouseleave', 'trayectorias-satelitales-posiciones', function () {
            mapa.getCanvas().style.cursor = '';
        });
    }

    function aplicarFiltroSatelite() {
        var id = filtroSatelite.value;
        ['huellas-satelitales', 'huellas-satelitales-borde',
            'trayectorias-satelitales-lineas', 'trayectorias-satelitales-posiciones']
            .forEach(function (capa) {
                var tipo = capa.indexOf('huellas-') === 0
                    ? 'huella'
                    : capa === 'trayectorias-satelitales-lineas' ? 'trayectoria' : 'posicion';
                var filtro = ['==', ['get', 'tipo'], tipo];
                if (id) {
                    filtro = ['all', filtro, ['==', ['get', 'norad_id'], Number(id)]];
                }
                mapa.setFilter(capa, filtro);
            });
        actualizarEstadoSatelites();
    }

    function actualizarOpcionesSatelites(datos) {
        var idSeleccionado = filtroSatelite.value;
        var porId = {};
        (datos.features || []).forEach(function (feature) {
            var propiedades = feature.properties || {};
            if (propiedades.tipo === 'posicion' && propiedades.norad_id !== undefined) {
                porId[propiedades.norad_id] = propiedades.nombre || 'Satélite';
            }
        });
        filtroSatelite.replaceChildren(new Option('Todos los satélites', ''));
        Object.keys(porId)
            .sort(function (a, b) {
                return porId[a].localeCompare(porId[b], 'es') || Number(a) - Number(b);
            })
            .forEach(function (id) {
                filtroSatelite.add(new Option(porId[id] + ' (NORAD ' + id + ')', id));
            });
        filtroSatelite.disabled = !mostrarSatelites.checked || !Object.keys(porId).length;
        filtroSatelite.value = porId[idSeleccionado] ? idSeleccionado : '';
        aplicarFiltroSatelite();
    }

    function actualizarEstadoSatelites() {
        if (!datosSatelites) return;
        var seleccionado = filtroSatelite.value
            ? filtroSatelite.options[filtroSatelite.selectedIndex].text
            : 'todos';
        var actualizado = datosSatelites.actualizado_tle
            ? new Date(datosSatelites.actualizado_tle).toLocaleString('es-CU')
            : 'fecha no disponible';
        var estadoDatos = datosSatelites.datos_vencidos
            ? 'TLE vencidos; se muestran los últimos datos guardados'
            : 'TLE actualizados: ' + actualizado;
        estadoSatelites.textContent =
            datosSatelites.satelites_sobre_cuba + ' satélite(s) con huella sobre Cuba en los próximos 90 min. ' +
            'Mostrando: ' + seleccionado + '. ' + estadoDatos + '. ' +
            (datosSatelites.aviso ? datosSatelites.aviso + ' ' : '') +
            'Fuente TLE: ' + (datosSatelites.fuente_tle || 'no identificada') +
            '. Franja geométrica aproximada (elevación ≥10°), no cobertura real del servicio.';
    }

    function actualizarTrayectoriasSatelitales() {
        if (!mostrarSatelites.checked) {
            estadoSatelites.textContent = 'Trayectorias satelitales ocultas.';
            filtroSatelite.disabled = true;
            mapa.getSource('trayectorias-satelitales').setData({
                type: 'FeatureCollection',
                features: []
            });
            return;
        }
        estadoSatelites.textContent = 'Calculando pasos de satélites activos sobre Cuba…';
        fetch(config.satelitesUrl, { cache: 'no-store' })
            .then(function (respuesta) {
                return respuesta.json().then(function (datos) {
                    if (!respuesta.ok) throw new Error(datos.error || 'No se pudieron cargar los datos orbitales.');
                    return datos;
                });
            })
            .then(function (datos) {
                datosSatelites = datos;
                mapa.getSource('trayectorias-satelitales').setData(datos);
                actualizarOpcionesSatelites(datos);
            })
            .catch(function (error) {
                estadoSatelites.textContent = error.message;
            });
    }

    function cargarPuntos() {
        return fetch(config.apiUrl).then(function (respuesta) {
            if (!respuesta.ok) throw new Error('No se pudieron cargar los puntos del mapa.');
            return respuesta.json();
        }).then(function (datos) {
            puntos = (datos.features || []).map(function (feature) {
                var coordenadas = feature.geometry.coordinates;
                var properties = Object.assign({}, feature.properties);
                var ubicacion = municipioDePunto(limites, coordenadas[1], coordenadas[0]) || {};
                properties.provincia = ubicacion.province || '';
                properties.municipio = ubicacion.municipality || '';
                properties.frecuencia_mhz = numeroFrecuencia(properties);
                properties.radio_km = radioCobertura(properties);
                return {
                    properties: properties,
                    coordinates: coordenadas,
                    frecuencia: properties.frecuencia_mhz,
                    radio: properties.radio_km
                };
            });
            actualizarMapa();
        });
    }

    mapa.on('error', function (evento) {
        if (evento.error) console.error('Error cargando el mapa directivo:', evento.error);
    });
    mapa.on('load', function () {
        cargarLimites().then(function (datos) {
            limites = datos;
            anadirLimites(mapa, limites);
            mapa.fitBounds(boundsFeature({
                geometry: { type: 'Polygon', coordinates: [[
                    [-85.2, 19.7], [-74.1, 19.7], [-74.1, 23.4], [-85.2, 23.4], [-85.2, 19.7]
                ]] }
            }), { padding: 24 });
            obtenerNombres(limites).forEach(function (nombre) {
                filtroProvincia.add(new Option(nombre, nombre));
            });
            actualizarMunicipios();
            anadirCapasPuntos();
            anadirCapasSatelites();
            actualizarTrayectoriasSatelitales();
            intervaloSatelites = window.setInterval(actualizarTrayectoriasSatelitales, 60000);
            return cargarPuntos();
        }).catch(function (error) {
            console.error('Error cargando el mapa directivo:', error);
            estado.textContent = error.message;
        });
    });

    filtroProvincia.addEventListener('change', function () {
        actualizarMunicipios();
        actualizarMapa();
    });
    filtroMunicipio.addEventListener('change', actualizarMapa);
    document.getElementById('mapa-aplicar-filtros').addEventListener('click', actualizarMapa);
    document.getElementById('mapa-limpiar-filtros').addEventListener('click', function () {
        filtroProvincia.value = '';
        filtroDesde.value = '';
        filtroHasta.value = '';
        actualizarMunicipios();
        filtroMunicipio.value = '';
        actualizarMapa();
    });
    mostrarSatelites.addEventListener('change', function () {
        if (intervaloSatelites) window.clearInterval(intervaloSatelites);
        if (mostrarSatelites.checked) {
            actualizarTrayectoriasSatelitales();
            intervaloSatelites = window.setInterval(actualizarTrayectoriasSatelitales, 60000);
        } else {
            filtroSatelite.disabled = true;
            if (mapa.getSource('trayectorias-satelitales')) {
                actualizarTrayectoriasSatelitales();
            }
        }
    });
    filtroSatelite.addEventListener('change', aplicarFiltroSatelite);
});
