import csv
import io
import re
from django.db import transaction

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from apps.mapa.models import PuntoMapa, ImportacionLog


# ============================================================
# MAPEO FLEXIBLE DE COLUMNAS
# ============================================================
MAPEO_COLUMNAS = {
    'nombre': ['nombre', 'name', 'dispositivo', 'device', 'equipo', 'emisora'],
    'tipo': ['tipo', 'type', 'categoria', 'category'],
    'latitud': ['latitud', 'lat', 'latitude', 'y'],
    'longitud': ['longitud', 'lon', 'lng', 'longitude', 'x'],
    'estado': ['estado', 'status', 'state'],
    'descripcion': ['descripcion', 'description', 'observaciones', 'notas'],
    'responsable': ['responsable', 'responsible', 'owner', 'encargado'],
}


# ============================================================
# PARSEO DE COORDENADAS
# ============================================================
def parsear_coordenada(valor):
    """
    Convierte distintos formatos de coordenadas a decimal.
    Acepta:
      - Float/int directo: 23.1136
      - String decimal: "23.1136"
      - Formato DMS con hemisferio: "20N0559", "75W4948"
      - Formato DMS con espacio: "230733 N", "821848 W"
      - Formato DMS con símbolos: "20°05'59\\"N"

    Devuelve: (valor_decimal, hemisferio)
      hemisferio es 'N', 'S', 'E', 'W' o None (si ya era decimal).
    """
    if valor is None:
        return None, None

    # Si ya es número
    if isinstance(valor, (int, float)):
        try:
            if PANDAS_AVAILABLE and pd.isna(valor):
                return None, None
        except Exception:
            pass
        return float(valor), None

    s = str(valor).strip().upper()
    if not s or s == 'NAN':
        return None, None

    # Caso 1: Decimal normal
    try:
        return float(s), None
    except ValueError:
        pass

    # Caso 2: Formato DMS con o sin símbolos/espacios
    # Extraer hemisferio
    hemisferio = None
    for h in ['N', 'S', 'E', 'W']:
        if h in s:
            hemisferio = h
            break

    # Extraer dígitos (ignorando el hemisferio)
    digitos = re.sub(r'[^0-9]', '', s)
    if not digitos or len(digitos) < 4:
        raise ValueError(f'Formato de coordenada no reconocido: {valor}')

    # Interpretar DDMMSS según cantidad de dígitos
    if len(digitos) == 6:
        grados = int(digitos[0:2])
        minutos = int(digitos[2:4])
        segundos = int(digitos[4:6])
    elif len(digitos) == 5:
        grados = int(digitos[0:1])
        minutos = int(digitos[1:3])
        segundos = int(digitos[3:5])
    elif len(digitos) == 7:
        grados = int(digitos[0:3])
        minutos = int(digitos[3:5])
        segundos = int(digitos[5:7])
    else:
        raise ValueError(f'Longitud de dígitos no soportada: {valor} ({len(digitos)} dígitos)')

    decimal = grados + minutos / 60.0 + segundos / 3600.0

    # Aplicar signo según hemisferio
    if hemisferio in ('S', 'W'):
        decimal = -decimal

    return round(decimal, 6), hemisferio


# ============================================================
# LECTURA DE ARCHIVOS
# ============================================================
def _detectar_columnas(df):
    """Detecta las columnas del archivo según nombres comunes."""
    columnas = {c.lower().strip(): c for c in df.columns}
    mapeo = {}
    for campo, alias in MAPEO_COLUMNAS.items():
        for a in alias:
            if a in columnas:
                mapeo[campo] = columnas[a]
                break
    return mapeo


def _leer_archivo(archivo):
    """
    Devuelve un DataFrame de pandas según el formato.
    Acepta:
      - Objeto archivo subido (tiene .read y .name)
      - Ruta de archivo (string)
    """
    # Si es string, es una ruta directa
    if isinstance(archivo, str):
        nombre = archivo.lower()
        if nombre.endswith('.csv'):
            for encoding in ['utf-8-sig', 'utf-8', 'latin-1']:
                try:
                    return pd.read_csv(archivo, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError('No se pudo leer el CSV con ningún encoding conocido')
        else:
            return pd.read_excel(archivo)

    # Si es un archivo subido (file-like object)
    nombre = archivo.name.lower()
    if nombre.endswith('.csv'):
        contenido = archivo.read()
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1']:
            try:
                texto = contenido.decode(encoding)
                return pd.read_csv(io.StringIO(texto))
            except UnicodeDecodeError:
                continue
        raise ValueError('No se pudo leer el CSV con ningún encoding conocido')
    else:
        return pd.read_excel(archivo)


# ============================================================
# PARSEO PRINCIPAL
# ============================================================
def parsear_archivo(archivo):
    """
    Lee el archivo y devuelve mapeo, registros y errores.
    `archivo` puede ser:
      - Un objeto de archivo subido (request.FILES[...])
      - Una ruta de archivo (str)
    """
    if not PANDAS_AVAILABLE:
        raise ImportError('pandas no está instalado. Ejecuta: pip install pandas openpyxl')

    # Solo hacemos seek si es un objeto con read
    if hasattr(archivo, 'seek') and not isinstance(archivo, str):
        try:
            archivo.seek(0)
        except Exception:
            pass

    df = _leer_archivo(archivo)
    df.columns = [str(c).strip() for c in df.columns]
    mapeo = _detectar_columnas(df)

    if 'latitud' not in mapeo or 'longitud' not in mapeo:
        raise ValueError(
            'El archivo debe tener columnas de latitud y longitud. '
            'Columnas detectadas: ' + ', '.join(df.columns)
        )

    registros = []
    errores = []

    for idx, fila in df.iterrows():
        num_fila = idx + 2
        try:
            val_lat = fila[mapeo['latitud']]
            val_lon = fila[mapeo['longitud']]

            lat, hem_lat = parsear_coordenada(val_lat)
            lon, hem_lon = parsear_coordenada(val_lon)

            if lat is None or lon is None:
                raise ValueError('Latitud o longitud vacía')

            # Detección de columnas invertidas
            if hem_lat in ('W', 'E'):
                lat, lon = lon, lat
                hem_lat, hem_lon = hem_lon, hem_lat

            if not (-90 <= lat <= 90):
                raise ValueError(f'Latitud fuera de rango: {lat} (original: {val_lat})')
            if not (-180 <= lon <= 180):
                raise ValueError(f'Longitud fuera de rango: {lon} (original: {val_lon})')

            # Nombre
            nombre = ''
            if 'nombre' in mapeo:
                nombre = str(fila[mapeo['nombre']]).strip()
            if not nombre or nombre.upper() == 'NAN':
                nombre = f'Punto fila {num_fila}'

            # Tipo
            tipo = 'GENERICO'
            if 'tipo' in mapeo:
                tipo_raw = str(fila[mapeo['tipo']]).strip().upper()
                tipos_validos = [t[0] for t in PuntoMapa.TIPO_CHOICES]
                for t in tipos_validos:
                    if t == tipo_raw or t.replace('_', ' ') == tipo_raw.replace('_', ' '):
                        tipo = t
                        break

            # Atributos extra
            columnas_usadas = set(mapeo.values())
            atributos = {}
            for col in df.columns:
                if col in columnas_usadas:
                    continue
                valor = fila[col]
                try:
                    if PANDAS_AVAILABLE and pd.isna(valor):
                        continue
                except Exception:
                    pass
                if hasattr(valor, 'item'):
                    valor = valor.item()
                if hasattr(valor, 'isoformat'):
                    valor = valor.isoformat()
                atributos[str(col)] = valor

            atributos['_coordenada_original'] = f"{val_lat} | {val_lon}"

            registro = {
                'nombre': nombre[:100],
                'tipo': tipo,
                'latitud': lat,
                'longitud': lon,
                'estado': 'ACTIVO',
                'descripcion': str(fila.get(mapeo.get('descripcion'), '') or '').strip(),
                'responsable': str(fila.get(mapeo.get('responsable'), '') or '').strip(),
                'atributos': atributos,
                'fila': num_fila,
            }
            registros.append(registro)

        except Exception as e:
            errores.append({
                'fila': num_fila,
                'error': str(e),
                'valores': {
                    'lat': str(fila.get(mapeo.get('latitud'), '')),
                    'lon': str(fila.get(mapeo.get('longitud'), '')),
                }
            })

    return mapeo, registros, errores


# ============================================================
# IMPORTACIÓN A LA BASE DE DATOS
# ============================================================
@transaction.atomic
def importar_registros(registros, actualizar=True, usuario=''):
    """Crea o actualiza los registros en la BD."""
    creados = 0
    actualizados = 0
    errores = []

    for reg in registros:
        try:
            defaults = {
                'tipo': reg['tipo'],
                'latitud': reg['latitud'],
                'longitud': reg['longitud'],
                'estado': reg['estado'],
                'descripcion': reg['descripcion'],
                'responsable': reg['responsable'],
                'atributos': reg['atributos'],
            }
            if actualizar:
                obj, created = PuntoMapa.objects.update_or_create(
                    nombre=reg['nombre'],
                    defaults=defaults
                )
            else:
                if PuntoMapa.objects.filter(nombre=reg['nombre']).exists():
                    errores.append({
                        'fila': reg.get('fila'),
                        'error': f"'{reg['nombre']}' ya existe"
                    })
                    continue
                obj = PuntoMapa.objects.create(nombre=reg['nombre'], **defaults)
                created = True

            if created:
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append({'fila': reg.get('fila'), 'error': str(e)})

    estado = 'EXITOSA'
    if errores and (creados or actualizados):
        estado = 'PARCIAL'
    elif errores and not (creados or actualizados):
        estado = 'FALLIDA'

    log = ImportacionLog.objects.create(
        nombre_archivo='importación',
        total_registros=len(registros),
        creados=creados,
        actualizados=actualizados,
        errores=len(errores),
        detalle_errores=errores,
        estado=estado,
        usuario=usuario,
    )
    return log