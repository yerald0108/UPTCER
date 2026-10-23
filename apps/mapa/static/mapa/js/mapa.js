document.addEventListener('DOMContentLoaded', function () {
    var config = window.MAPA_CONFIG || {};

    // ============================================================
    // 1. MAPA
    // ============================================================
    var map = L.map('map').setView([22.0, -79.0], 7);

    // ============================================================
    // 2. CAPAS BASE
    // ============================================================
    var capaCalles = L.tileLayer(
        'https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
        { attribution: '&copy; OpenStreetMap France', subdomains: 'abc', maxZoom: 20 }
    );
    var capaSatelite = L.tileLayer(
        'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        { attribution: 'Imagery &copy; Google', maxZoom: 21 }
    );
    var capaTopo = L.tileLayer(
        'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        { attribution: 'Map data &copy; OSM, SRTM | Style &copy; OpenTopoMap', maxZoom: 17 }
    );
    var capaHibrido = L.tileLayer(
        'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        { attribution: 'Imagery &copy; Google', maxZoom: 21 }
    );

    capaCalles.addTo(map);

    L.control.layers({
        "Calles": capaCalles,
        "Satelite": capaSatelite,
        "Topografico": capaTopo,
        "Hibrido": capaHibrido
    }, null, { position: 'topright', collapsed: true }).addTo(map);

    L.control.scale({ imperial: false, metric: true }).addTo(map);

    // ============================================================
    // 3. CLUSTER
    // ============================================================
    var markers = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 15
    });

    // ============================================================
    // 4. ICONOS
    // ============================================================
    var iconosUrls = config.iconos || {
        'GENERICO': '/static/mapa/img/marker-grey.png'
    };
    var shadowUrl = config.shadowUrl || '/static/mapa/img/marker-shadow.png';

    function crearIcono(tipoKey) {
        var url = iconosUrls[tipoKey] || iconosUrls['GENERICO'];
        return L.icon({
            iconUrl: url,
            shadowUrl: shadowUrl,
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41]
        });
    }

    // ============================================================
    // 5. CARGAR PUNTOS EXISTENTES
    // ============================================================
    var apiUrl = config.apiUrl || '/mapa/api/puntos.geojson';

    fetch(apiUrl)
        .then(function (response) {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.json();
        })
        .then(function (data) {
            L.geoJSON(data, {
                pointToLayer: function (feature, latlng) {
                    var tipoKey = feature.properties.tipo || 'GENERICO';
                    return L.marker(latlng, { icon: crearIcono(tipoKey) });
                },
                onEachFeature: function (feature, layer) {
                    layer.on('click', function () {
                        mostrarInfo(feature.properties);
                    });
                    var props = feature.properties;
                    var popup = document.createElement('div');
                    var titulo = document.createElement('strong');
                    titulo.textContent = props.nombre || 'Sin nombre';
                    popup.appendChild(titulo);

                    var equipos = props.equipos || [];
                    if (equipos.length) {
                        var detalle = document.createElement('div');
                        detalle.textContent = equipos.map(function (equipo) {
                            return [equipo.descripcion, equipo.marca, equipo.modelo]
                                .filter(Boolean).join(' ');
                        }).filter(Boolean).join(', ');
                        popup.appendChild(detalle);
                    }
                    layer.bindPopup(popup);
                }
            }).addTo(markers);
            map.addLayer(markers);
        })
        .catch(function (error) {
            console.error('Error cargando puntos:', error);
        });

    // ============================================================
    // 6. UTILIDADES DE INFO
    // ============================================================
    function mostrarInfo(props) {
        document.getElementById('info-nombre').textContent = props.nombre || 'Sin nombre';
        document.getElementById('info-tipo').textContent = props.tipo_display || props.tipo || 'N/D';
        document.getElementById('info-estado').textContent = props.estado || 'N/D';
        document.getElementById('info-responsable').textContent = props.responsable || 'N/D';
        document.getElementById('info-descripcion').textContent = props.descripcion || '';

        var excluidos = [
            'id','nombre','tipo','tipo_display','estado','descripcion',
            'responsable','fecha_instalacion','ultima_revision','direccion'
        ];
        var attrContainer = document.getElementById('info-atributos');
        attrContainer.innerHTML = '';
        for (var key in props) {
            if (excluidos.indexOf(key) === -1 && props[key] !== null && props[key] !== '') {
                var p = document.createElement('p');
                var labelBonito = key.replace(/_/g, ' ').replace(/\b\w/g, function (c) {
                    return c.toUpperCase();
                });
                var label = document.createElement('strong');
                label.textContent = labelBonito + ': ';
                p.appendChild(label);
                var valor = props[key];
                if (Array.isArray(valor)) {
                    valor = valor.map(function (equipo) {
                        return [equipo.descripcion, equipo.marca, equipo.modelo]
                            .filter(Boolean).join(' ');
                    }).filter(Boolean).join(', ');
                } else if (typeof valor === 'object') {
                    valor = JSON.stringify(valor);
                }
                p.appendChild(document.createTextNode(valor));
                attrContainer.appendChild(p);
            }
        }

        document.getElementById('info-panel').style.display = 'block';
    }

    var closePanel = document.getElementById('close-panel');
    if (closePanel) {
        closePanel.addEventListener('click', function () {
            document.getElementById('info-panel').style.display = 'none';
        });
    }

    // ============================================================
    // 7. BUSCADOR Y CREACIÓN DE PUNTOS
    // ============================================================
    window.searchMarker = null;

    window.buscarLugar = function() {
        var query = document.getElementById('search-input').value;
        if (!query) return;

        // Nominatim API de OpenStreetMap
        var url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' + encodeURIComponent(query);

        fetch(url)
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data && data.length > 0) {
                    var lat = parseFloat(data[0].lat);
                    var lon = parseFloat(data[0].lon);
                    var displayName = data[0].display_name;

                    // Volar a la ubicación
                    map.flyTo([lat, lon], 14, { duration: 1.5 });

                    // Quitar marcador anterior
                    if (window.searchMarker) {
                        map.removeLayer(window.searchMarker);
                    }

                    // URL para crear el punto con las coordenadas
                    var urlCrear = config.urlCrear + '?lat=' + lat + '&lon=' + lon;

                    // Popup con botón de crear
                    var popupHtml = `
                        <div style="text-align:center;">
                            <b>📍 Resultado</b><br>
                            <small>${displayName.substring(0, 50)}...</small><br><br>
                            <a href="${urlCrear}" class="btn btn-primary btn-sm" style="background:#0d6efd;color:white;padding:5px 10px;border-radius:4px;text-decoration:none;font-weight:bold;">
                                ➕ Crear punto aquí
                            </a>
                        </div>
                    `;

                    window.searchMarker = L.marker([lat, lon]).addTo(map)
                        .bindPopup(popupHtml)
                        .openPopup();

                } else {
                    alert('No se encontró la dirección. Intenta con otros términos.');
                }
            })
            .catch(function(error) {
                console.error('Error en búsqueda:', error);
                alert('Error al buscar. Revisa tu conexión a internet.');
            });
    };
});