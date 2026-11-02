import * as maplibregl from '../vendor/maplibre-gl.mjs';

var protocoloRegistrado = false;
var capaFuente = 'uptcer-cuba';

function registrarProtocolo() {
    if (protocoloRegistrado) return;
    if (!window.pmtiles || !window.basemaps) {
        throw new Error('No se pudieron cargar las bibliotecas locales del mapa.');
    }
    maplibregl.addProtocol('pmtiles', new window.pmtiles.Protocol().tile);
    protocoloRegistrado = true;
}

function crearEstiloBase() {
    registrarProtocolo();
    var capas = window.basemaps.layers(
        capaFuente,
        window.basemaps.namedFlavor('light'),
        { lang: 'es' }
    );
    capas.forEach(function (capa) {
        var fuentes = capa.layout && capa.layout['text-font'];
        if (fuentes) {
            capa.layout['text-font'] = fuentes.map(function (fuente) {
                return fuente === 'Noto Sans Italic' ? 'Noto Sans Regular' : fuente;
            });
        }
    });
    return {
        version: 8,
        glyphs: window.location.origin + window.MAPA_GLYPHS_URL,
        sprite: new URL(window.MAPA_SPRITES_URL, window.location.origin).toString(),
        sources: {
            [capaFuente]: {
                type: 'vector',
                url: 'pmtiles://' + window.MAPA_BASEMAP_URL,
                attribution: '<a href="https://protomaps.com">Protomaps</a> | <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors (ODbL)</a>'
            }
        },
        layers: capas
    };
}

function crearMapa(elemento, centro, zoom) {
    var mapa = new maplibregl.Map({
        container: elemento,
        style: crearEstiloBase(),
        center: centro || [-79, 22],
        zoom: zoom || 6,
        maxZoom: 14,
        attributionControl: true,
        hash: false
    });
    mapa.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapa.addControl(new maplibregl.ScaleControl({ unit: 'metric' }));
    return mapa;
}

function normalizar(texto) {
    return String(texto || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLocaleLowerCase('es')
        .trim();
}

function cargarLimites(url) {
    return fetch(url || window.MAPA_LIMITES_URL).then(function (respuesta) {
        if (!respuesta.ok) throw new Error('No se pudieron cargar los límites locales de Cuba.');
        return respuesta.json();
    }).then(function (datos) {
        if (!datos || datos.type !== 'FeatureCollection' || !Array.isArray(datos.features)) {
            throw new Error('El archivo local de límites no tiene un formato GeoJSON válido.');
        }
        return datos;
    });
}

function anadirLimites(mapa, limites) {
    if (mapa.getSource('limites-cuba')) return;
    mapa.addSource('limites-cuba', { type: 'geojson', data: limites });
    mapa.addLayer({
        id: 'limites-cuba-fill',
        type: 'fill',
        source: 'limites-cuba',
        paint: { 'fill-color': '#3b82a0', 'fill-opacity': 0.045 }
    });
    mapa.addLayer({
        id: 'limites-cuba-line',
        type: 'line',
        source: 'limites-cuba',
        paint: { 'line-color': '#256383', 'line-width': 1.1, 'line-opacity': 0.85 }
    });
}

function buscarMunicipio(limites, consulta) {
    if (!limites) return null;
    var clave = normalizar(consulta);
    if (!clave) return null;
    return limites.features.find(function (feature) {
        var propiedades = feature.properties || {};
        return normalizar(propiedades.municipality) === clave ||
            normalizar(propiedades.province) === clave;
    }) || limites.features.find(function (feature) {
        var propiedades = feature.properties || {};
        return normalizar(propiedades.municipality).indexOf(clave) !== -1 ||
            normalizar(propiedades.province).indexOf(clave) !== -1;
    }) || null;
}

function puntoEnAnillo(longitud, latitud, anillo) {
    var dentro = false;
    for (var i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
        var xi = anillo[i][0];
        var yi = anillo[i][1];
        var xj = anillo[j][0];
        var yj = anillo[j][1];
        if (((yi > latitud) !== (yj > latitud)) &&
            longitud < ((xj - xi) * (latitud - yi)) / (yj - yi) + xi) {
            dentro = !dentro;
        }
    }
    return dentro;
}

function puntoEnPoligono(longitud, latitud, anillos) {
    return anillos.length > 0 && puntoEnAnillo(longitud, latitud, anillos[0]) &&
        !anillos.slice(1).some(function (hueco) {
            return puntoEnAnillo(longitud, latitud, hueco);
        });
}

function municipioDePunto(limites, latitud, longitud) {
    var encontrado = null;
    limites.features.some(function (feature) {
        var geometria = feature.geometry || {};
        var coordenadas = geometria.coordinates || [];
        var contiene = geometria.type === 'Polygon'
            ? puntoEnPoligono(longitud, latitud, coordenadas)
            : geometria.type === 'MultiPolygon' && coordenadas.some(function (poligono) {
                return puntoEnPoligono(longitud, latitud, poligono);
            });
        if (contiene) {
            encontrado = feature.properties || {};
            return true;
        }
        return false;
    });
    return encontrado;
}

function obtenerNombres(limites) {
    var provincias = {};
    limites.features.forEach(function (feature) {
        var provincia = feature.properties && feature.properties.province;
        if (provincia) provincias[provincia] = true;
    });
    return Object.keys(provincias).sort(function (a, b) { return a.localeCompare(b, 'es'); });
}

function boundsFeature(feature) {
    var limites = new maplibregl.LngLatBounds();
    function recorrer(coordenadas) {
        if (typeof coordenadas[0] === 'number' && typeof coordenadas[1] === 'number') {
            limites.extend(coordenadas);
        } else {
            coordenadas.forEach(recorrer);
        }
    }
    recorrer(feature.geometry.coordinates);
    return limites;
}

function crearCobertura(longitud, latitud, radioKm, properties) {
    var coordenadas = [];
    var radioMetros = radioKm * 1000;
    var radioTierra = 6371008.8;
    var latitudRadianes = latitud * Math.PI / 180;
    var longitudRadianes = longitud * Math.PI / 180;

    for (var i = 0; i <= 64; i++) {
        var rumbo = 2 * Math.PI * i / 64;
        var distanciaAngular = radioMetros / radioTierra;
        var latitudDestino = Math.asin(
            Math.sin(latitudRadianes) * Math.cos(distanciaAngular) +
            Math.cos(latitudRadianes) * Math.sin(distanciaAngular) * Math.cos(rumbo)
        );
        var longitudDestino = longitudRadianes + Math.atan2(
            Math.sin(rumbo) * Math.sin(distanciaAngular) * Math.cos(latitudRadianes),
            Math.cos(distanciaAngular) - Math.sin(latitudRadianes) * Math.sin(latitudDestino)
        );
        coordenadas.push([longitudDestino * 180 / Math.PI, latitudDestino * 180 / Math.PI]);
    }

    return {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [coordenadas] },
        properties: properties || {}
    };
}

function escapar(texto) {
    var elemento = document.createElement('span');
    elemento.textContent = String(texto || '');
    return elemento.innerHTML;
}

export {
    maplibregl,
    crearMapa,
    cargarLimites,
    anadirLimites,
    buscarMunicipio,
    municipioDePunto,
    obtenerNombres,
    boundsFeature,
    crearCobertura,
    escapar
};
