import {
    anadirLimites,
    boundsFeature,
    buscarMunicipio,
    cargarLimites,
    crearCobertura,
    crearMapa,
    maplibregl
} from './mapa-offline.js?v=3';

document.addEventListener('DOMContentLoaded', function () {
    var config = window.MAPA_CONFIG || {};
    var mapa = crearMapa('map');
    var puntos = [];
    var estado = document.getElementById('mapa-estado');
    var popup = new maplibregl.Popup({ closeButton: true, closeOnClick: true });

    function radioKm(properties) {
        var radio = Number(properties.radio_km);
        return Number.isFinite(radio) && radio > 0 && radio <= 1000 ? radio : null;
    }

    function renderizarPuntos(datos) {
        puntos = datos.features || [];
        var conRadio = puntos.map(function (feature) {
            return {
                feature: feature,
                radio: radioKm(feature.properties || {}),
                coordenadas: feature.geometry.coordinates
            };
        }).filter(function (punto) { return punto.radio !== null; });
        var solapamientos = {};

        for (var i = 0; i < conRadio.length; i++) {
            for (var j = i + 1; j < conRadio.length; j++) {
                var lat1 = conRadio[i].coordenadas[1] * Math.PI / 180;
                var lat2 = conRadio[j].coordenadas[1] * Math.PI / 180;
                var deltaLatitud = lat2 - lat1;
                var deltaLongitud = (conRadio[j].coordenadas[0] - conRadio[i].coordenadas[0]) * Math.PI / 180;
                var haversine = Math.sin(deltaLatitud / 2) ** 2 +
                    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLongitud / 2) ** 2;
                var distancia = 6371.0088 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
                if (distancia < conRadio[i].radio + conRadio[j].radio) {
                    solapamientos[conRadio[i].feature.properties.id] = true;
                    solapamientos[conRadio[j].feature.properties.id] = true;
                }
            }
        }

        var coberturas = conRadio.map(function (punto) {
            var propiedades = punto.feature.properties || {};
            var solapa = Boolean(solapamientos[propiedades.id]);
            return crearCobertura(
                punto.coordenadas[0],
                punto.coordenadas[1],
                punto.radio,
                {
                    id: propiedades.id,
                    nombre: propiedades.nombre || 'Punto sin nombre',
                    radio_km: punto.radio,
                    solapa: solapa,
                    color: solapa ? '#dc2626' : '#2563eb'
                }
            );
        });

        mapa.addSource('cobertura-puntos', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: coberturas }
        });
        mapa.addLayer({
            id: 'cobertura-puntos-fill',
            type: 'fill',
            source: 'cobertura-puntos',
            paint: {
                'fill-color': ['get', 'color'],
                'fill-opacity': 0.16
            }
        });
        mapa.addLayer({
            id: 'cobertura-puntos-line',
            type: 'line',
            source: 'cobertura-puntos',
            paint: {
                'line-color': ['get', 'color'],
                'line-width': 2
            }
        });
        var featuresPuntos = puntos.map(function (feature) {
            var propiedades = Object.assign({}, feature.properties);
            propiedades.solapa = Boolean(solapamientos[propiedades.id]);
            return {
                type: 'Feature',
                geometry: feature.geometry,
                properties: propiedades
            };
        });
        mapa.addSource('puntos-mapa', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: featuresPuntos }
        });
        mapa.addLayer({
            id: 'puntos-mapa-circulos',
            type: 'circle',
            source: 'puntos-mapa',
            paint: {
                'circle-radius': 7,
                'circle-color': [
                    'case',
                    ['boolean', ['get', 'solapa'], false],
                    '#dc2626',
                    '#155e9a'
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff'
            }
        });

        mapa.on('click', 'puntos-mapa-circulos', function (evento) {
            var feature = evento.features && evento.features[0];
            if (!feature) return;
            mostrarPunto(feature, evento.lngLat);
        });
        mapa.on('mouseenter', 'puntos-mapa-circulos', function () {
            mapa.getCanvas().style.cursor = 'pointer';
        });
        mapa.on('mouseleave', 'puntos-mapa-circulos', function () {
            mapa.getCanvas().style.cursor = '';
        });
        estado.textContent = puntos.length + ' punto(s). Los círculos son radios manuales estimados; rojo indica solapamiento geométrico.';
    }

    function mostrarPunto(feature, ubicacion) {
        var props = feature.properties || {};
        var contenido = document.createElement('div');
        var titulo = document.createElement('strong');
        titulo.textContent = props.nombre || 'Punto sin nombre';
        contenido.appendChild(titulo);
        [
            ['Tipo', props.tipo_display || props.tipo],
            ['Estado', props.estado],
            ['Frecuencia', props.frecuencia_mhz ? props.frecuencia_mhz + ' MHz' : null],
            ['Radio estimado', radioKm(props) ? radioKm(props) + ' km' : null],
            ['Responsable', props.responsable],
            ['Dirección', props.direccion_instalacion || props.direccion]
        ].forEach(function (item) {
            if (!item[1]) return;
            var linea = document.createElement('div');
            linea.textContent = item[0] + ': ' + item[1];
            contenido.appendChild(linea);
        });
        popup.setLngLat(ubicacion).setDOMContent(contenido).addTo(mapa);
    }

    function buscarLocal(limites, consulta) {
        var clave = normalizar(consulta);
        var punto = puntos.find(function (feature) {
            var props = feature.properties || {};
            return normalizar(props.nombre).indexOf(clave) !== -1 ||
                normalizar(props.direccion || props.direccion_instalacion).indexOf(clave) !== -1;
        });
        if (punto) {
            var coordenadas = punto.geometry.coordinates;
            mapa.flyTo({ center: coordenadas, zoom: 14 });
            mostrarPunto(punto, { lng: coordenadas[0], lat: coordenadas[1] });
            return true;
        }
        var municipio = buscarMunicipio(limites, consulta);
        if (municipio) {
            mapa.fitBounds(boundsFeature(municipio), { maxZoom: 12, padding: 24 });
            return true;
        }
        return false;
    }

    function normalizar(texto) {
        return String(texto || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLocaleLowerCase('es')
            .trim();
    }

    window.buscarLugar = function () {
        var consulta = document.getElementById('search-input').value.trim();
        if (!consulta) return;
        if (window.MAPA_LIMITES && buscarLocal(window.MAPA_LIMITES, consulta)) return;

        var url = new URL('https://nominatim.openstreetmap.org/search');
        url.searchParams.set('format', 'jsonv2');
        url.searchParams.set('limit', '1');
        url.searchParams.set('q', consulta);
        fetch(url.toString())
            .then(function (respuesta) {
                if (!respuesta.ok) throw new Error('Búsqueda en línea no disponible.');
                return respuesta.json();
            })
            .then(function (resultados) {
                if (!resultados.length) throw new Error('No se encontró el lugar.');
                var resultado = resultados[0];
                var coordenadas = [Number(resultado.lon), Number(resultado.lat)];
                mapa.flyTo({ center: coordenadas, zoom: 14 });
                var urlCrear = new URL(config.urlCrear, window.location.origin);
                urlCrear.searchParams.set('lat', coordenadas[1]);
                urlCrear.searchParams.set('lon', coordenadas[0]);
                var contenido = document.createElement('div');
                contenido.appendChild(document.createTextNode(resultado.display_name || consulta));
                var enlace = document.createElement('a');
                enlace.href = urlCrear.toString();
                enlace.textContent = 'Crear punto aquí';
                enlace.style.display = 'block';
                contenido.appendChild(enlace);
                popup.setLngLat(coordenadas).setDOMContent(contenido).addTo(mapa);
            })
            .catch(function () {
                window.alert('No se encontró el punto localmente. La búsqueda de direcciones requiere Internet; también puede ubicarlo haciendo clic en el mapa.');
            });
    };

    mapa.on('error', function (evento) {
        if (evento.error) console.error('Error cargando el mapa offline:', evento.error);
    });

    mapa.on('load', function () {
        cargarLimites()
            .then(function (limites) {
                window.MAPA_LIMITES = limites;
                anadirLimites(mapa, limites);
                return fetch(config.apiUrl);
            })
            .then(function (respuesta) {
                if (!respuesta.ok) throw new Error('No se pudieron cargar los puntos del mapa.');
                return respuesta.json();
            })
            .then(renderizarPuntos)
            .catch(function (error) {
                console.error('Error cargando datos locales del mapa:', error);
                estado.textContent = error.message;
            });
    });

    document.getElementById('close-panel').addEventListener('click', function () {
        document.getElementById('info-panel').style.display = 'none';
    });
});
