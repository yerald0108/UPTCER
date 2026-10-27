import json
import os
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode
from django.views.decorators.http import require_GET, require_POST
from apps.licencias.models import Licencia

from .forms import ImportarArchivoForm
from .models import PuntoMapa, ImportacionLog
from .services.importador import parsear_archivo, importar_registros


def _url_volver(request):
    candidata = request.GET.get('next') or request.META.get('HTTP_REFERER')
    if candidata and url_has_allowed_host_and_scheme(
        candidata,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidata
    return reverse('accounts:dashboard')


# ============================================================
# VISTAS DEL MAPA
# ============================================================

@login_required
def mapa_view(request):
    """Vista principal del mapa."""
    return render(request, 'mapa/mapa.html', {
        'url_volver': _url_volver(request),
    })


def seleccionar_ubicacion_view(request):
    """Selector de coordenadas para el formulario F43."""
    return render(request, 'mapa/seleccionar_ubicacion.html', {
        'consulta_inicial': request.GET.get('q', '').strip(),
        'lat_inicial': request.GET.get('lat', ''),
        'lon_inicial': request.GET.get('lon', ''),
    })


@require_GET
@login_required
def api_puntos_geojson(request):
    """API que devuelve todos los puntos activos en formato GeoJSON."""
    puntos = PuntoMapa.objects.filter(estado='ACTIVO').select_related(
        'solicitud__solicitante',
        'solicitud__licencia',
    )
    if request.user.es_persona_natural:
        puntos = puntos.filter(solicitud__solicitante=request.user)
    features = []
    for punto in puntos:
        feature = punto.geojson_feature
        solicitud = punto.solicitud
        if solicitud:
            properties = feature['properties']
            properties['solicitud_numero'] = solicitud.numero
            properties['solicitante'] = solicitud.solicitante.get_nombre_completo()
            properties['direccion_instalacion'] = solicitud.direccion_instalacion
            try:
                licencia = solicitud.licencia
            except Licencia.DoesNotExist:
                licencia = None
            if licencia:
                properties['licencia_numero'] = licencia.numero
                properties['licencia_estado'] = (
                    'Vencida'
                    if licencia.estado == Licencia.ESTADO_VIGENTE and not licencia.es_vigente
                    else licencia.get_estado_display()
                )
                properties['licencia_fecha_vencimiento'] = (
                    licencia.fecha_vencimiento.isoformat()
                    if licencia.fecha_vencimiento else 'Sin vencimiento'
                )
        features.append(feature)
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    return JsonResponse(geojson, safe=False)


# ============================================================
# CREAR PUNTO DESDE EL MAPA (con coordenadas prellenadas)
# ============================================================

@staff_member_required(login_url='admin:login')
def crear_punto_view(request):
    """Página con mini-mapa para crear un punto manualmente."""
    # Recibir latitud y longitud desde la URL si vienen del buscador
    lat = request.GET.get('lat', '')
    lon = request.GET.get('lon', '')
    
    return render(request, 'mapa/crear_punto.html', {
        'lat_inicial': lat,
        'lon_inicial': lon,
        'url_volver': _url_volver(request),
        'url_mapa': f"{reverse('mapa:mapa')}?{urlencode({'next': _url_volver(request)})}",
    })


@require_POST
@staff_member_required(login_url='admin:login')
def api_crear_punto(request):
    """Endpoint AJAX que recibe datos y crea un punto en la BD."""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        nombre = (data.get('nombre') or '').strip()
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        tipo = (data.get('tipo') or 'GENERICO').strip().upper()

        if not nombre:
            return JsonResponse({'ok': False, 'error': 'El nombre es obligatorio'}, status=400)
        if latitud is None or longitud is None:
            return JsonResponse({'ok': False, 'error': 'Latitud y longitud son obligatorias'}, status=400)

        try:
            latitud = float(latitud)
            longitud = float(longitud)
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'error': 'Latitud/longitud inválidas'}, status=400)

        if not (-90 <= latitud <= 90):
            return JsonResponse({'ok': False, 'error': 'Latitud fuera de rango'}, status=400)
        if not (-180 <= longitud <= 180):
            return JsonResponse({'ok': False, 'error': 'Longitud fuera de rango'}, status=400)

        tipos_validos = [t[0] for t in PuntoMapa.TIPO_CHOICES]
        if tipo not in tipos_validos:
            tipo = 'GENERICO'

        if PuntoMapa.objects.filter(nombre=nombre).exists():
            return JsonResponse({
                'ok': False,
                'error': f'Ya existe un punto con el nombre "{nombre}"'
            }, status=400)

        atributos = data.get('atributos', {})
        if isinstance(atributos, str):
            try:
                atributos = json.loads(atributos)
            except json.JSONDecodeError:
                atributos = {}

        punto = PuntoMapa.objects.create(
            nombre=nombre,
            tipo=tipo,
            latitud=latitud,
            longitud=longitud,
            estado=data.get('estado', 'ACTIVO'),
            descripcion=data.get('descripcion', ''),
            responsable=data.get('responsable', ''),
            atributos=atributos,
        )

        return JsonResponse({
            'ok': True,
            'punto': punto.geojson_feature,
            'mensaje': f'Punto "{punto.nombre}" creado correctamente',
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ============================================================
# IMPORTAR EXCEL / CSV
# ============================================================

@login_required
def importar_view(request):
    preview = None
    errores = []
    mapeo = {}
    total_registros = 0
    form = ImportarArchivoForm()

    if request.method == 'POST':
        # ----- Paso 2: confirmar la importación -----
        if 'confirmar' in request.POST:
            ruta = request.session.get('archivo_importacion')
            actualizar = request.POST.get('actualizar', 'true') == 'true'
            if not ruta or not os.path.exists(ruta):
                messages.error(request, 'El archivo temporal ya no está disponible. Vuelve a subirlo.')
                return redirect('mapa:importar')
            try:
                # Pasamos la RUTA directamente (no un file object)
                _, registros, _ = parsear_archivo(ruta)

                log = importar_registros(
                    registros,
                    actualizar=actualizar,
                    usuario=request.user.username if request.user.is_authenticated else ''
                )

                # Borrar archivo temporal
                try:
                    os.remove(ruta)
                except OSError:
                    pass
                request.session.pop('archivo_importacion', None)
                request.session.pop('archivo_nombre', None)
                request.session.pop('actualizar', None)

                messages.success(
                    request,
                    f'✅ Importación completada: {log.creados} creados, '
                    f'{log.actualizados} actualizados, {log.errores} errores.'
                )
                return redirect('mapa:mapa')
            except Exception as e:
                messages.error(request, f'Error al importar: {e}')
                return redirect('mapa:importar')

        # ----- Paso 1: subir y previsualizar -----
        form = ImportarArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                archivo = form.cleaned_data['archivo']

                ruta_relativa = default_storage.save(
                    f'tmp_import/{archivo.name}',
                    archivo
                )
                ruta_abs = os.path.join(settings.MEDIA_ROOT, ruta_relativa)

                request.session['archivo_importacion'] = ruta_abs
                request.session['archivo_nombre'] = archivo.name
                request.session['actualizar'] = form.cleaned_data['actualizar_existentes']

                # Parsear desde la ruta
                mapeo, registros, errores = parsear_archivo(ruta_abs)
                preview = registros[:20]
                total_registros = len(registros)
            except Exception as e:
                messages.error(request, f'Error procesando el archivo: {e}')
        else:
            messages.error(request, 'Revisa el archivo.')

    contexto = {
        'form': form,
        'preview': preview,
        'errores': errores,
        'mapeo': mapeo,
        'total_registros': total_registros,
        'actualizar': request.session.get('actualizar', True),
        'url_volver': _url_volver(request),
        'url_mapa': f"{reverse('mapa:mapa')}?{urlencode({'next': _url_volver(request)})}",
    }
    return render(request, 'mapa/importar.html', contexto)