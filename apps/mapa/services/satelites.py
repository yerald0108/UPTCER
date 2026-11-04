import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone as django_timezone
from sgp4.api import Satrec, jday


URL_TLE_ACTIVOS = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
FUENTES_TLE_ALTERNATIVAS = (
    (
        'CelesTrak visual (subset)',
        'https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle',
    ),
    (
        'AMSAT amateur (subset)',
        'https://www.amsat.org/tle/current/nasabare.txt',
    ),
)
AVISO_FUENTE_PARCIAL = (
    'La fuente principal de satélites activos está limitada temporalmente; '
    'se muestra un grupo alternativo parcial.'
)
HORAS_ENTRE_ACTUALIZACIONES = 6
HORAS_ENTRE_INTENTOS = 2
MINUTOS_PRONOSTICO = 90
INTERVALO_TRAYECTORIA_MINUTOS = 1
INTERVALO_HUELLA_MINUTOS = 5
ELEVACION_MINIMA_GRADOS = 10
RADIO_TIERRA_KM = 6371.0
REGION_CUBA = (-85.2, 19.7, -74.1, 23.4)
CAPA_CACHE = Path('datos_satelites') / 'activos.tle'


class DatosOrbitalesNoDisponibles(Exception):
    pass


def _ruta_cache():
    return Path(settings.MEDIA_ROOT) / CAPA_CACHE


def _parsear_tle(texto):
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    satelites = []
    for indice, linea in enumerate(lineas[:-1]):
        if not linea.startswith('1 ') or not lineas[indice + 1].startswith('2 '):
            continue
        nombre = lineas[indice - 1] if indice > 0 and not lineas[indice - 1].startswith(('1 ', '2 ')) else ''
        try:
            satelite = Satrec.twoline2rv(linea, lineas[indice + 1])
        except ValueError:
            continue
        satelites.append((nombre or f'NORAD {satelite.satnum}', satelite.satnum, satelite))
    return satelites


@lru_cache(maxsize=2)
def _leer_satelites_cache(ruta, fecha_modificacion):
    return tuple(_parsear_tle(Path(ruta).read_text(encoding='utf-8')))


def _guardar_cache(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=ruta.parent,
            prefix='activos-',
            suffix='.tmp',
            delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            archivo.write(contenido)
        os.replace(temporal, ruta)
    finally:
        if temporal and temporal.exists():
            temporal.unlink()


def cargar_elementos_orbitales():
    ruta = _ruta_cache()
    cache_existe = ruta.is_file()
    cache_fecha = (
        datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc)
        if cache_existe else None
    )
    caducado = (
        cache_fecha is None
        or django_timezone.now() - cache_fecha >= timedelta(hours=HORAS_ENTRE_ACTUALIZACIONES)
    )
    ruta_intento = ruta.with_suffix('.attempt')
    ruta_intento_alternativas = ruta.with_suffix('.fallback-attempt')
    intento_fecha = (
        datetime.fromtimestamp(ruta_intento.stat().st_mtime, tz=timezone.utc)
        if ruta_intento.is_file() else None
    )
    puede_intentar = (
        intento_fecha is None
        or django_timezone.now() - intento_fecha >= timedelta(hours=HORAS_ENTRE_INTENTOS)
    )
    intento_alternativas_fecha = (
        datetime.fromtimestamp(ruta_intento_alternativas.stat().st_mtime, tz=timezone.utc)
        if ruta_intento_alternativas.is_file() else None
    )
    puede_intentar_alternativas = (
        intento_alternativas_fecha is None
        or django_timezone.now() - intento_alternativas_fecha
        >= timedelta(hours=HORAS_ENTRE_INTENTOS)
    )
    aviso = ''
    fuente = 'CelesTrak active'

    if caducado:
        fuentes = []
        if puede_intentar:
            fuentes.append(('CelesTrak active', URL_TLE_ACTIVOS))
            _guardar_cache(ruta_intento, django_timezone.now().isoformat())
        if not cache_existe and puede_intentar_alternativas:
            fuentes.extend(FUENTES_TLE_ALTERNATIVAS)
            _guardar_cache(
                ruta_intento_alternativas,
                django_timezone.now().isoformat(),
            )
        error_fuente = None
        for nombre_fuente, url_fuente in fuentes:
            try:
                solicitud = Request(
                    url_fuente,
                    headers={'User-Agent': 'UPTCER/1.0 satellite map'},
                )
                with urlopen(solicitud, timeout=15) as respuesta:
                    contenido = respuesta.read().decode('utf-8')
                if not _parsear_tle(contenido):
                    raise DatosOrbitalesNoDisponibles(
                        'La fuente orbital no devolvió TLE válidos.'
                    )
                _guardar_cache(ruta, contenido)
                _guardar_cache(ruta.with_suffix('.source'), nombre_fuente)
                cache_fecha = django_timezone.now()
                fuente = nombre_fuente
                if nombre_fuente != 'CelesTrak active':
                    aviso = AVISO_FUENTE_PARCIAL
                error_fuente = None
                break
            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                UnicodeDecodeError,
                DatosOrbitalesNoDisponibles,
            ) as error:
                error_fuente = error
        if error_fuente and not cache_existe:
            detalle = (
                'La fuente principal y las alternativas no están disponibles. '
                'Conéctese a Internet y vuelva a intentarlo.'
            )
            raise DatosOrbitalesNoDisponibles(
                'No hay datos orbitales guardados ni se pudieron obtener. ' + detalle
            ) from error_fuente
        if error_fuente:
            aviso = 'No se pudo actualizar la fuente orbital; se usan los últimos datos guardados.'
        elif not fuentes and cache_existe:
            aviso = 'Los datos orbitales están vencidos; se reintentará su actualización más adelante.'
        elif not fuentes:
            raise DatosOrbitalesNoDisponibles(
                'No hay datos orbitales guardados. Se agotó el intervalo de reintento; '
                'se volverá a intentar más adelante.'
            )

    if not ruta.is_file():
        raise DatosOrbitalesNoDisponibles(
            'No hay datos orbitales guardados. Conéctese a Internet y vuelva a intentarlo más tarde.'
        )
    try:
        satelites = _leer_satelites_cache(str(ruta), ruta.stat().st_mtime)
    except OSError as error:
        raise DatosOrbitalesNoDisponibles('No se pudieron leer los datos orbitales guardados.') from error
    ruta_fuente = ruta.with_suffix('.source')
    if ruta_fuente.is_file():
        try:
            fuente = ruta_fuente.read_text(encoding='utf-8')
        except OSError:
            fuente = 'Fuente orbital guardada'
    elif cache_existe:
        fuente = 'Fuente orbital guardada'
    if not aviso and fuente in {nombre for nombre, _ in FUENTES_TLE_ALTERNATIVAS}:
        aviso = AVISO_FUENTE_PARCIAL
    if not satelites:
        raise DatosOrbitalesNoDisponibles('El archivo orbital guardado no contiene TLE válidos.')
    return satelites, cache_fecha, aviso, fuente


def _posicion_geografica(satelite, instante):
    juliano, fraccion = jday(
        instante.year,
        instante.month,
        instante.day,
        instante.hour,
        instante.minute,
        instante.second + instante.microsecond / 1_000_000,
    )
    error, posicion, _ = satelite.sgp4(juliano, fraccion)
    if error:
        return None

    x, y, z = posicion
    siglos = (juliano + fraccion - 2451545.0) / 36525.0
    gmst = math.radians(
        (280.46061837 + 360.98564736629 * (juliano + fraccion - 2451545.0)
         + 0.000387933 * siglos ** 2 - siglos ** 3 / 38710000.0) % 360
    )
    x_tierra = math.cos(gmst) * x + math.sin(gmst) * y
    y_tierra = -math.sin(gmst) * x + math.cos(gmst) * y
    radio = math.sqrt(x_tierra ** 2 + y_tierra ** 2 + z ** 2)
    latitud = math.degrees(math.atan2(z, math.sqrt(x_tierra ** 2 + y_tierra ** 2)))
    longitud = (math.degrees(math.atan2(y_tierra, x_tierra)) + 180) % 360 - 180
    altitud = radio - RADIO_TIERRA_KM
    return longitud, latitud, altitud


def _radio_huella_km(altitud):
    if altitud <= 0:
        return 0
    elevacion = math.radians(ELEVACION_MINIMA_GRADOS)
    angulo_central = math.acos(
        RADIO_TIERRA_KM / (RADIO_TIERRA_KM + altitud) * math.cos(elevacion)
    ) - elevacion
    return RADIO_TIERRA_KM * max(angulo_central, 0)


def _distancia_a_region(longitud, latitud):
    lon_min, lat_min, lon_max, lat_max = REGION_CUBA
    lon_cercana = min(max(longitud, lon_min), lon_max)
    lat_cercana = min(max(latitud, lat_min), lat_max)
    delta_lat = math.radians(lat_cercana - latitud)
    delta_lon = math.radians(lon_cercana - longitud)
    lat1 = math.radians(latitud)
    lat2 = math.radians(lat_cercana)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return RADIO_TIERRA_KM * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def _poligono_huella(longitud, latitud, radio_km):
    coordenadas = []
    distancia_angular = radio_km / RADIO_TIERRA_KM
    latitud_rad = math.radians(latitud)
    longitud_rad = math.radians(longitud)
    for indice in range(37):
        rumbo = 2 * math.pi * indice / 36
        latitud_destino = math.asin(
            math.sin(latitud_rad) * math.cos(distancia_angular)
            + math.cos(latitud_rad) * math.sin(distancia_angular) * math.cos(rumbo)
        )
        longitud_destino = longitud_rad + math.atan2(
            math.sin(rumbo) * math.sin(distancia_angular) * math.cos(latitud_rad),
            math.cos(distancia_angular) - math.sin(latitud_rad) * math.sin(latitud_destino),
        )
        coordenadas.append([
            (math.degrees(longitud_destino) + 180) % 360 - 180,
            math.degrees(latitud_destino),
        ])
    return [coordenadas]


def _feature(tipo, geometria, propiedades):
    return {
        'type': 'Feature',
        'geometry': geometria,
        'properties': {'tipo': tipo, **propiedades},
    }


@lru_cache(maxsize=2)
def _calcular_geojson(minuto, ruta, fecha_modificacion):
    satelites = _leer_satelites_cache(ruta, fecha_modificacion)
    inicio = datetime.fromtimestamp(minuto * 60, tz=timezone.utc)
    features = []
    for nombre, norad_id, satelite in satelites:
        posiciones = []
        huellas = []
        cruza_cuba = False
        for paso in range(MINUTOS_PRONOSTICO + 1):
            posicion = _posicion_geografica(
                satelite,
                inicio + timedelta(minutes=paso * INTERVALO_TRAYECTORIA_MINUTOS),
            )
            if not posicion:
                continue
            longitud, latitud, altitud = posicion
            radio = _radio_huella_km(altitud)
            posiciones.append([longitud, latitud])
            if radio and _distancia_a_region(longitud, latitud) <= radio:
                cruza_cuba = True
                if paso % INTERVALO_HUELLA_MINUTOS == 0:
                    huellas.append(_poligono_huella(longitud, latitud, radio))
        if not cruza_cuba or not posiciones:
            continue
        propiedades = {
            'nombre': nombre,
            'norad_id': norad_id,
            'elevacion_minima_grados': ELEVACION_MINIMA_GRADOS,
        }
        features.append(_feature(
            'trayectoria',
            {'type': 'LineString', 'coordinates': posiciones},
            propiedades,
        ))
        features.append(_feature(
            'posicion',
            {'type': 'Point', 'coordinates': posiciones[0]},
            propiedades,
        ))
        if huellas:
            features.append(_feature(
                'huella',
                {'type': 'MultiPolygon', 'coordinates': huellas},
                propiedades,
            ))
    return {'type': 'FeatureCollection', 'features': features}


def obtener_trayectorias_satelitales(ahora=None):
    satelites, fecha_tle, aviso, fuente = cargar_elementos_orbitales()
    ruta = _ruta_cache()
    minuto = int((ahora or django_timezone.now()).timestamp() // 60)
    geojson = _calcular_geojson(minuto, str(ruta), ruta.stat().st_mtime)
    return {
        **geojson,
        'generado': datetime.fromtimestamp(minuto * 60, tz=timezone.utc).isoformat(),
        'actualizado_tle': fecha_tle.isoformat() if fecha_tle else None,
        'datos_vencidos': bool(fecha_tle and django_timezone.now() - fecha_tle >= timedelta(hours=HORAS_ENTRE_ACTUALIZACIONES)),
        'aviso': aviso,
        'fuente_tle': fuente,
        'total_satelites_activos': len(satelites),
        'satelites_sobre_cuba': sum(
            1 for feature in geojson['features'] if feature['properties']['tipo'] == 'posicion'
        ),
    }
