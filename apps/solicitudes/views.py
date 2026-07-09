import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from .models import Solicitud, HistorialSolicitud
from .forms import FormularioF43
from apps.notificaciones.servicios import (
    notificar_solicitud_nueva,
    notificar_cambio_estado,
    notificar_derivacion_especialista,
    notificar_criterio_tecnico,
)
from apps.licencias.servicios import generar_licencia
from apps.equipos.models import Equipo, CategoriaEquipo


# ─── Nueva solicitud F43 ──────────────────────────────────────────────────────
@never_cache
@login_required
def nueva_solicitud_f43(request):
    if not request.user.es_persona_natural:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = FormularioF43(request.POST, request.FILES)
        equipos_json = request.POST.get('equipos_json', '[]')
        try:
            equipos = json.loads(equipos_json)
        except json.JSONDecodeError:
            equipos = []

        if form.is_valid():
            if not equipos:
                messages.error(request, 'Debe agregar al menos un equipo a la solicitud.')
                return render(request, 'solicitudes/f43.html', {
                    'form': form,
                    'today': timezone.now().date().isoformat(),
                })

            solicitud = Solicitud(
                flujo       = Solicitud.FLUJO_F43,
                estado      = Solicitud.ESTADO_ENVIADA,
                solicitante = request.user,
                observaciones_solicitante = form.cleaned_data.get('observaciones_solicitante', ''),
            )

            if form.cleaned_data.get('documento_adjunto'):
                solicitud.documento_adjunto = form.cleaned_data['documento_adjunto']

            datos_f43 = {
                'nombre_apellidos':       form.cleaned_data['nombre_apellidos'],
                'numero_pasaporte':       form.cleaned_data['numero_pasaporte'],
                'pais_residencia':        form.cleaned_data['pais_residencia'],
                'direccion_residencia':   form.cleaned_data['direccion_residencia'],
                'correo_electronico':     form.cleaned_data['correo_electronico'],
                'telefono':               form.cleaned_data['telefono'],
                'provincia':              form.cleaned_data['provincia'],
                'modo_importacion':       form.cleaned_data['modo_importacion'],
                'numero_vuelo':           form.cleaned_data.get('numero_vuelo', ''),
                'fecha_arribo':           str(form.cleaned_data.get('fecha_arribo', '')),
                'pais_procedencia':       form.cleaned_data.get('pais_procedencia', ''),
                'aduana_acceso':          form.cleaned_data.get('aduana_acceso', ''),
                'lugar_acceso':           form.cleaned_data.get('lugar_acceso', ''),
                'numero_rad':             form.cleaned_data.get('numero_rad', ''),
                'objetivo_importacion':   form.cleaned_data['objetivo_importacion'],
                'objetivo_otros_detalle': form.cleaned_data.get('objetivo_otros_detalle', ''),
                'periodo_importacion':    form.cleaned_data['periodo_importacion'],
                'tiempo_solicitado':      str(form.cleaned_data.get('tiempo_solicitado', '')),
                'firma_ci':               request.POST.get('firma_ci', ''),
                'fecha_solicitud':        request.POST.get('fecha_solicitud', ''),
                'equipos':                equipos,
            }

            solicitud.equipo_descripcion = json.dumps(datos_f43, ensure_ascii=False)
            solicitud.save()

            # Registrar en historial
            HistorialSolicitud.objects.create(
                solicitud       = solicitud,
                estado_anterior = '',
                estado_nuevo    = Solicitud.ESTADO_ENVIADA,
                usuario         = request.user,
                observacion     = 'Solicitud creada y enviada por el solicitante.',
            )

            # Notificar a operadores
            notificar_solicitud_nueva(solicitud)

            messages.success(
                request,
                f'Solicitud {solicitud.numero} enviada correctamente. El operador la revisará en breve.'
            )
            return redirect('solicitudes:detalle', pk=solicitud.pk)

        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
            return render(request, 'solicitudes/f43.html', {
                'form': form,
                'today': timezone.now().date().isoformat(),
            })

    else:
        form = FormularioF43(initial={
            'nombre_apellidos':   request.user.get_nombre_completo(),
            'correo_electronico': request.user.email,
            'telefono':           request.user.telefono,
        })

    return render(request, 'solicitudes/f43.html', {
        'form': form,
        'today': timezone.now().date().isoformat(),
    })


# ─── Mis solicitudes ──────────────────────────────────────────────────────────
@never_cache
@login_required
def mis_solicitudes(request):
    solicitudes_qs = Solicitud.objects.filter(
        solicitante=request.user
    ).order_by('-fecha_creacion')

    paginator = Paginator(solicitudes_qs, 10)
    pagina    = request.GET.get('pagina', 1)

    try:
        solicitudes = paginator.page(pagina)
    except PageNotAnInteger:
        solicitudes = paginator.page(1)
    except EmptyPage:
        solicitudes = paginator.page(paginator.num_pages)

    return render(request, 'solicitudes/mis_solicitudes.html', {
        'solicitudes': solicitudes,
        'paginator':   paginator,
    })


# ─── Detalle de solicitud ─────────────────────────────────────────────────────
@never_cache
@login_required
def detalle_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    usuario   = request.user

    # Control de acceso
    if usuario.es_persona_natural and solicitud.solicitante != usuario:
        messages.error(request, 'No tiene permisos para ver esta solicitud.')
        return redirect('solicitudes:mis_solicitudes')

    # Cargar datos F43 guardados en JSON
    datos_f43 = {}
    if solicitud.equipo_descripcion:
        try:
            datos_f43 = json.loads(solicitud.equipo_descripcion)
        except json.JSONDecodeError:
            datos_f43 = {}

    equipos   = datos_f43.get('equipos', [])
    historial = solicitud.historial.select_related('usuario').all()

    contexto = {
        'solicitud': solicitud,
        'datos_f43': datos_f43,
        'equipos':   equipos,
        'historial': historial,
        'puede_gestionar': usuario.es_operador or usuario.es_directivo,
        'puede_evaluar':   usuario.es_especialista,
        'ESTADOS': Solicitud.ESTADOS,
        'volver_url': request.GET.get('volver', ''),
    }

    return render(request, 'solicitudes/detalle.html', contexto)


# ─── Cambiar estado (operador) ────────────────────────────────────────────────
@never_cache
@login_required
def cambiar_estado(request, pk):
    if request.method != 'POST':
        return redirect('solicitudes:detalle', pk=pk)

    solicitud = get_object_or_404(Solicitud, pk=pk)
    usuario   = request.user

    if not (usuario.es_operador or usuario.es_directivo or usuario.es_especialista):
        messages.error(request, 'No tiene permisos para realizar esta acción.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)
        return redirect('solicitudes:detalle', pk=pk)

    # No permitir cambios en solicitudes ya resueltas
    if solicitud.esta_resuelta:
        messages.error(request, 'Esta solicitud ya fue resuelta y no puede modificarse.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Solicitud ya resuelta.'}, status=400)
        return redirect('solicitudes:detalle', pk=pk)

    estado_nuevo  = request.POST.get('estado_nuevo', '').strip()
    observacion   = request.POST.get('observacion', '').strip()
    estados_validos = [e[0] for e in Solicitud.ESTADOS]

    if estado_nuevo not in estados_validos:
        messages.error(request, 'Estado no válido.')
        return redirect('solicitudes:detalle', pk=pk)

    estado_anterior = solicitud.estado

    # Actualizar solicitud
    solicitud.estado = estado_nuevo

    if estado_nuevo in [Solicitud.ESTADO_APROBADA, Solicitud.ESTADO_DENEGADA]:
        solicitud.fecha_resolucion = timezone.now()

    if not solicitud.operador_asignado and usuario.es_operador:
        solicitud.operador_asignado = usuario

    if observacion:
        if usuario.es_especialista:
            solicitud.observaciones_tecnicas = observacion
        else:
            solicitud.observaciones_operador = observacion

    solicitud.save()

    # Registrar en historial
    HistorialSolicitud.objects.create(
        solicitud       = solicitud,
        estado_anterior = estado_anterior,
        estado_nuevo    = estado_nuevo,
        usuario         = usuario,
        observacion     = observacion,
    )

    # Notificaciones automáticas
    # Siempre notificar al solicitante
    notificar_cambio_estado(solicitud, estado_anterior, usuario)

    # Si se deriva al especialista
    if estado_nuevo == Solicitud.ESTADO_EN_REVISION and solicitud.equipo_no_listado:
        notificar_derivacion_especialista(solicitud)

    # Si el especialista emitió criterio técnico
    if usuario.es_especialista and observacion:
        notificar_criterio_tecnico(solicitud)
        
     # Generar licencia automáticamente si la solicitud fue aprobada
    if estado_nuevo == Solicitud.ESTADO_APROBADA:
        generar_licencia(solicitud, usuario)

    messages.success(
        request,
        f'Estado de la solicitud {solicitud.numero} actualizado a "{solicitud.get_estado_display()}".'
    )

    # Si la petición es AJAX devolver JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        licencia_url = None
        if estado_nuevo == Solicitud.ESTADO_APROBADA:
            try:
                licencia_url = solicitud.licencia.numero
            except Exception:
                pass

        return JsonResponse({
            'ok':            True,
            'estado_nuevo':  estado_nuevo,
            'estado_label':  solicitud.get_estado_display(),
            'clase_badge':   solicitud.clase_badge,
            'licencia_numero': licencia_url,
        })

    return redirect('solicitudes:detalle', pk=pk)


# ─── Lista de solicitudes (operador/directivo) ────────────────────────────────
@never_cache
@login_required
def lista_solicitudes(request):
    usuario = request.user

    if not (usuario.es_operador or usuario.es_directivo or usuario.es_especialista):
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    solicitudes_qs = Solicitud.objects.select_related(
        'solicitante', 'operador_asignado'
    ).order_by('-fecha_creacion')

    # Filtros
    estado = request.GET.get('estado', '')
    flujo  = request.GET.get('flujo', '')
    q      = request.GET.get('q', '').strip()

    if estado:
        solicitudes_qs = solicitudes_qs.filter(estado=estado)
    if flujo:
        solicitudes_qs = solicitudes_qs.filter(flujo=flujo)
    if q:
        solicitudes_qs = solicitudes_qs.filter(
            Q(numero__icontains=q) |
            Q(solicitante__nombre__icontains=q) |
            Q(solicitante__apellidos__icontains=q)
        )

    paginator = Paginator(solicitudes_qs, 15)
    pagina    = request.GET.get('pagina', 1)

    try:
        solicitudes = paginator.page(pagina)
    except PageNotAnInteger:
        solicitudes = paginator.page(1)
    except EmptyPage:
        solicitudes = paginator.page(paginator.num_pages)

    # Calcular días en cola solo para solicitudes pendientes (página actual)
    ahora = timezone.now()
    for s in solicitudes:
        s.dias_en_cola = (ahora - s.fecha_creacion).days if s.esta_pendiente else None

    return render(request, 'solicitudes/lista.html', {
        'solicitudes':   solicitudes,
        'paginator':     paginator,
        'estado_actual': estado,
        'flujo_actual':  flujo,
        'busqueda':      q,
        'ESTADOS':       Solicitud.ESTADOS,
        'FLUJOS':        Solicitud.FLUJOS,
    })
    
# ─── Cola de evaluaciones del especialista ────────────────────────────────────
@never_cache
@login_required
def cola_evaluaciones(request):
    if not request.user.es_especialista:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    pendientes = Solicitud.objects.filter(
        equipo_no_listado=True,
        estado=Solicitud.ESTADO_EN_REVISION
    ).select_related('solicitante').order_by('fecha_creacion')

    completadas = Solicitud.objects.filter(
        equipo_no_listado=True,
        estado__in=[Solicitud.ESTADO_APROBADA, Solicitud.ESTADO_DENEGADA]
    ).select_related('solicitante').order_by('-fecha_resolucion')[:10]

    return render(request, 'solicitudes/especialista/cola.html', {
        'pendientes':  pendientes,
        'completadas': completadas,
        'total_pendientes': pendientes.count(),
    })


# ─── Vista de evaluación técnica ──────────────────────────────────────────────
@never_cache
@login_required
def evaluar_solicitud(request, pk):
    if not request.user.es_especialista:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    solicitud = get_object_or_404(Solicitud, pk=pk)

    if not solicitud.equipo_no_listado:
        messages.error(request, 'Esta solicitud no requiere evaluación técnica.')
        return redirect('solicitudes:detalle', pk=pk)

    datos_f43 = {}
    equipos   = []
    try:
        datos_f43 = json.loads(solicitud.equipo_descripcion or '{}')
        equipos   = datos_f43.get('equipos', [])
    except (json.JSONDecodeError, TypeError):
        pass

    historial = solicitud.historial.select_related('usuario').all()

    if request.method == 'POST':
        accion           = request.POST.get('accion', '')
        criterio         = request.POST.get('criterio_tecnico', '').strip()
        banda_detectada  = request.POST.get('banda_detectada', '')
        cumple_normativa = request.POST.get('cumple_normativa', '') == '1'
        agregar_catalogo = request.POST.get('agregar_catalogo', '') == '1'

        if not criterio:
            messages.error(request, 'Debe escribir el criterio técnico antes de continuar.')
            return redirect('solicitudes:evaluar', pk=pk)

        if accion not in ['aprobar', 'denegar']:
            messages.error(request, 'Acción no válida.')
            return redirect('solicitudes:evaluar', pk=pk)

        estado_anterior = solicitud.estado
        estado_nuevo    = (
            Solicitud.ESTADO_APROBADA if accion == 'aprobar'
            else Solicitud.ESTADO_DENEGADA
        )

        # Guardar criterio técnico y datos de evaluación
        evaluacion = {
            'banda_detectada':  banda_detectada,
            'cumple_normativa': cumple_normativa,
            'criterio':         criterio,
            'evaluador':        request.user.get_nombre_completo(),
        }

        solicitud.estado               = estado_nuevo
        solicitud.observaciones_tecnicas = json.dumps(evaluacion, ensure_ascii=False)
        solicitud.fecha_resolucion     = timezone.now()
        solicitud.save()

        # Historial
        HistorialSolicitud.objects.create(
            solicitud       = solicitud,
            estado_anterior = estado_anterior,
            estado_nuevo    = estado_nuevo,
            usuario         = request.user,
            observacion     = criterio,
        )

        # Notificaciones
        notificar_cambio_estado(solicitud, estado_anterior, request.user)
        notificar_criterio_tecnico(solicitud)

        # Generar licencia si se aprueba
        if estado_nuevo == Solicitud.ESTADO_APROBADA:
            generar_licencia(solicitud, request.user)

        # Agregar equipo al catálogo si se solicitó
        if agregar_catalogo and accion == 'aprobar':
            nombre_equipo = request.POST.get('cat_nombre', '').strip()
            marca_equipo  = request.POST.get('cat_marca', '').strip()
            modelo_equipo = request.POST.get('cat_modelo', '').strip()
            categoria_id  = request.POST.get('cat_categoria', '')
            banda_cat     = request.POST.get('cat_banda', 'no_aplica')

            if nombre_equipo and marca_equipo and modelo_equipo and categoria_id:
                try:
                    categoria = CategoriaEquipo.objects.get(pk=categoria_id)
                    Equipo.objects.get_or_create(
                        marca=marca_equipo,
                        modelo=modelo_equipo,
                        defaults={
                            'nombre':           nombre_equipo,
                            'categoria':        categoria,
                            'banda_frecuencia': banda_cat,
                            'requiere_permiso': True,
                            'activo':           True,
                        }
                    )
                    messages.success(request, f'Equipo "{nombre_equipo}" agregado al catálogo.')
                except CategoriaEquipo.DoesNotExist:
                    pass

        accion_texto = 'aprobada' if accion == 'aprobar' else 'denegada'
        messages.success(
            request,
            f'Solicitud {solicitud.numero} {accion_texto} con criterio técnico registrado.'
        )
        return redirect('solicitudes:cola_evaluaciones')

    categorias = CategoriaEquipo.objects.all()

    return render(request, 'solicitudes/especialista/evaluar.html', {
        'solicitud':  solicitud,
        'datos_f43':  datos_f43,
        'equipos':    equipos,
        'historial':  historial,
        'categorias': categorias,
        'BANDAS':     Equipo.BANDAS,
    })