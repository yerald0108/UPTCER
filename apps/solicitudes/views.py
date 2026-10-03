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
    notificar_derivacion_superior,
    notificar_criterio_tecnico,
    notificar_pendiente_aprobacion,
)
from apps.licencias.servicios import generar_factura, generar_licencia
from apps.equipos.models import Equipo, CategoriaEquipo

# ─── Resolver categoría y estado según equipos declarados ────────────────────
def _resolver_categoria_y_estado(equipos):
    """
    Analiza los equipos declarados en el F43 y determina:
    - La categoría de especialidad (según el primer equipo listado del catálogo)
    - El estado inicial de la solicitud
    - Si hay equipos no listados

    Reglas:
    - Si todos los equipos son del catálogo → ENVIADA al especialista de área
    - Si algún equipo NO está en el catálogo → EN_REVISION_SUPERIOR directo
    - La categoría se obtiene del modelo Equipo en la base de datos
    """
    from apps.equipos.models import Equipo

    # Mapa de categoría de equipo → categoría de solicitud
    # Ajusta este mapa según las categorías reales de tu catálogo
    CATEGORIA_EQUIPO_MAP = {
        'Teléfonos móviles':       Solicitud.CATEGORIA_MOVIL,
        'Routers y access points': Solicitud.CATEGORIA_INTERNET,
        'Tablets y computadoras':  Solicitud.CATEGORIA_INTERNET,
        'Equipos de radio':        Solicitud.CATEGORIA_RADIOFARO,
        'Cámaras y vigilancia':    Solicitud.CATEGORIA_INTERNET,
        'Wearables y accesorios':  Solicitud.CATEGORIA_MOVIL,
        'Equipos satelitales':     Solicitud.CATEGORIA_MARITIMO,
        'Modems y equipos de red': Solicitud.CATEGORIA_INTERNET,
    }

    hay_no_listado = False
    categoria      = ''

    for equipo_data in equipos:
        listado   = equipo_data.get('listado', False)
        equipo_id = equipo_data.get('equipoId', '')

        if not listado or not equipo_id:
            # Equipo no listado en catálogo
            hay_no_listado = True
        else:
            # Equipo del catálogo — leer su categoría
            if not categoria:
                try:
                    equipo_obj = Equipo.objects.select_related('categoria').get(pk=equipo_id)
                    nombre_cat = equipo_obj.categoria.nombre
                    categoria  = CATEGORIA_EQUIPO_MAP.get(nombre_cat, Solicitud.CATEGORIA_INTERNET)
                except Equipo.DoesNotExist:
                    hay_no_listado = True

    # Determinar estado inicial
    if hay_no_listado:
        estado = Solicitud.ESTADO_EN_REVISION_SUPERIOR
    else:
        estado = Solicitud.ESTADO_ENVIADA

    # Si no se pudo determinar categoría, dejar vacía
    # (el especialista superior la asignará)
    return categoria, estado, hay_no_listado

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
                    'equipos_iniciales': equipos_json,
                })

            # Determinar categoría y estado según equipos declarados
            categoria, estado_inicial, hay_no_listado = _resolver_categoria_y_estado(equipos)

            solicitud = Solicitud(
                flujo       = Solicitud.FLUJO_F43,
                categoria   = categoria,
                estado      = estado_inicial,
                solicitante = request.user,
                equipo_no_listado = hay_no_listado,
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
                estado_nuevo    = estado_inicial,
                usuario         = request.user,
                observacion     = 'Solicitud creada y enviada por el solicitante.',
            )

            # Notificar al especialista correspondiente
            notificar_solicitud_nueva(solicitud)

            messages.success(
                request,
                f'Solicitud {solicitud.numero} enviada correctamente. El especialista la revisará en breve.'
            )
            return redirect('solicitudes:detalle', pk=solicitud.pk)

        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
            return render(request, 'solicitudes/f43.html', {
                'form': form,
                'today': timezone.now().date().isoformat(),
                'equipos_iniciales': equipos_json,
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
        'puede_gestionar':  usuario.es_directivo,
        'puede_evaluar':    usuario.es_especialista_base,
        'puede_eval_sup':   usuario.es_especialista_superior,
        'ESTADOS': Solicitud.ESTADOS,
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

    if not (usuario.es_especialista_base or usuario.es_especialista_superior or usuario.es_directivo):
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

    if observacion:
        if usuario.es_especialista_base or usuario.es_especialista_superior:
            solicitud.observaciones_tecnicas = observacion
        elif usuario.es_directivo:
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
    notificar_cambio_estado(solicitud, estado_anterior, usuario)

    # Si se deriva al especialista superior
    if estado_nuevo == Solicitud.ESTADO_EN_REVISION_SUPERIOR and solicitud.equipo_no_listado:
        notificar_derivacion_superior(solicitud)

    # Si el especialista superior emitió criterio técnico
    if usuario.es_especialista_superior and observacion:
        notificar_criterio_tecnico(solicitud)

    # Notificar al directivo si está pendiente de aprobación
    if estado_nuevo == Solicitud.ESTADO_PENDIENTE_APROBACION:
        notificar_pendiente_aprobacion(solicitud)

    # Al aprobar el directivo se genera la factura (la licencia se genera al pagar)
    if estado_nuevo == Solicitud.ESTADO_APROBADA:
        generar_factura(solicitud, usuario)

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


# ─── Lista de solicitudes ─────────────────────────────────────────────────────
@never_cache
@login_required
def lista_solicitudes(request):
    usuario = request.user

    if not (usuario.es_especialista_base or usuario.es_especialista_superior or usuario.es_directivo):
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    solicitudes_qs = Solicitud.objects.select_related(
        'solicitante'
    ).order_by('-fecha_creacion')

    # Filtro automático por categoría según rol del especialista
    CATEGORIA_ROL = {
        'especialista_radiofaro': 'radiofaro',
        'especialista_movil':     'movil',
        'especialista_maritimo':  'maritimo',
        'especialista_internet':  'internet',
    }

    if usuario.es_especialista_base:
        # Cada especialista solo ve su categoría en estado enviada o en revisión
        categoria_usuario = CATEGORIA_ROL.get(usuario.rol, '')
        solicitudes_qs = solicitudes_qs.filter(
            categoria=categoria_usuario,
            estado__in=[
                Solicitud.ESTADO_ENVIADA,
                Solicitud.ESTADO_EN_REVISION,
            ]
        )
    elif usuario.es_especialista_superior:
        # El especialista superior solo ve las escaladas a él
        solicitudes_qs = solicitudes_qs.filter(
            estado=Solicitud.ESTADO_EN_REVISION_SUPERIOR
        )
    # El directivo ve todas

    # Filtros manuales adicionales
    estado = request.GET.get('estado', '')
    flujo  = request.GET.get('flujo', '')
    q      = request.GET.get('q', '').strip()

    if estado:
        solicitudes_qs = solicitudes_qs.filter(estado=estado)
    if flujo:
        solicitudes_qs = solicitudes_qs.filter(flujo=flujo)

    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    if fecha_desde:
        solicitudes_qs = solicitudes_qs.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        solicitudes_qs = solicitudes_qs.filter(fecha_creacion__date__lte=fecha_hasta)

    if q:
        solicitudes_qs = solicitudes_qs.filter(
            Q(numero__icontains=q) |
            Q(solicitante__nombre__icontains=q) |
            Q(solicitante__apellidos__icontains=q)
        )

    # Filtro de supervisión directiva (solo directivo)
    supervision = request.GET.get('supervision', '')
    if usuario.es_directivo:
        if supervision == 'revisadas':
            solicitudes_qs = solicitudes_qs.filter(revisada_directivo=True)
        elif supervision == 'pendientes':
            solicitudes_qs = solicitudes_qs.filter(revisada_directivo=False)

    paginator = Paginator(solicitudes_qs, 15)
    pagina    = request.GET.get('pagina', 1)

    try:
        solicitudes = paginator.page(pagina)
    except PageNotAnInteger:
        solicitudes = paginator.page(1)
    except EmptyPage:
        solicitudes = paginator.page(paginator.num_pages)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'solicitudes/tabla_solicitudes.html', {
            'solicitudes':   solicitudes,
            'estado_actual': estado,
            'flujo_actual':  flujo,
            'fecha_desde':   fecha_desde,
            'fecha_hasta':   fecha_hasta,
            'busqueda':      q,
        })

    return render(request, 'solicitudes/lista.html', {
        'solicitudes':   solicitudes,
        'paginator':     paginator,
        'estado_actual': estado,
        'flujo_actual':  flujo,
        'fecha_desde':   fecha_desde,
        'fecha_hasta':   fecha_hasta,
        'busqueda':      q,
        'supervision':   supervision,
        'ESTADOS':       Solicitud.ESTADOS,
        'FLUJOS':        Solicitud.FLUJOS,
    })


# ─── Cola de evaluaciones del especialista superior ───────────────────────────
@never_cache
@login_required
def cola_evaluaciones(request):
    if not request.user.es_especialista_superior:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    # Pendientes: equipos no listados escalados al superior
    pendientes_qs = Solicitud.objects.filter(
        equipo_no_listado=True,
        estado=Solicitud.ESTADO_EN_REVISION_SUPERIOR
    ).select_related('solicitante').order_by('fecha_creacion')

    paginator_pendientes = Paginator(pendientes_qs, 10)
    pagina_pendientes = request.GET.get('pagina_pendientes', 1)

    try:
        pendientes = paginator_pendientes.page(pagina_pendientes)
    except PageNotAnInteger:
        pendientes = paginator_pendientes.page(1)
    except EmptyPage:
        pendientes = paginator_pendientes.page(paginator_pendientes.num_pages)

    # Completadas por el superior
    completadas_qs = Solicitud.objects.filter(
        equipo_no_listado=True,
        estado__in=[
            Solicitud.ESTADO_PENDIENTE_APROBACION,
            Solicitud.ESTADO_APROBADA,
            Solicitud.ESTADO_DENEGADA,
        ]
    ).select_related('solicitante').order_by('-fecha_resolucion')

    paginator_completadas = Paginator(completadas_qs, 10)
    pagina_completadas = request.GET.get('pagina_completadas', 1)

    try:
        completadas = paginator_completadas.page(pagina_completadas)
    except PageNotAnInteger:
        completadas = paginator_completadas.page(1)
    except EmptyPage:
        completadas = paginator_completadas.page(paginator_completadas.num_pages)

    return render(request, 'solicitudes/especialista/cola.html', {
        'pendientes':             pendientes,
        'completadas':            completadas,
        'total_pendientes':       pendientes_qs.count(),
        'paginator_pendientes':   paginator_pendientes,
        'paginator_completadas':  paginator_completadas,
    })

# ─── Vista de evaluación técnica ──────────────────────────────────────────────
@never_cache
@login_required
def evaluar_solicitud(request, pk):
    if not request.user.es_especialista_superior:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    solicitud = get_object_or_404(Solicitud, pk=pk)

    if not solicitud.equipo_no_listado:
        messages.error(request, 'Esta solicitud no requiere evaluación de equipo no listado.')
        return redirect('solicitudes:detalle', pk=pk)

    # Solo se puede evaluar si está en revisión superior
    if solicitud.estado != Solicitud.ESTADO_EN_REVISION_SUPERIOR:
        messages.error(request, 'Esta solicitud no está en estado de revisión superior.')
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
            Solicitud.ESTADO_PENDIENTE_APROBACION if accion == 'aprobar'
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

        # Si el superior aprobó, notificar al directivo para aprobación final
        if estado_nuevo == Solicitud.ESTADO_PENDIENTE_APROBACION:
            notificar_pendiente_aprobacion(solicitud)
            
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

        if accion == 'aprobar':
            messages.success(
                request,
                f'Solicitud {solicitud.numero} evaluada correctamente. Pendiente de aprobación por el directivo.'
            )
        else:
            messages.success(
                request,
                f'Solicitud {solicitud.numero} denegada con criterio técnico registrado.'
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
    
# ─── Marcar / desmarcar supervisión directiva ─────────────────────────────────
@never_cache
@login_required
def marcar_supervision(request, pk):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para realizar esta acción.')
        return redirect('solicitudes:detalle', pk=pk)

    if request.method != 'POST':
        return redirect('solicitudes:detalle', pk=pk)

    solicitud = get_object_or_404(Solicitud, pk=pk)

    if solicitud.revisada_directivo:
        # Desmarcar
        solicitud.revisada_directivo       = False
        solicitud.fecha_revision_directivo = None
        solicitud.revisada_por             = None
        solicitud.save(update_fields=[
            'revisada_directivo',
            'fecha_revision_directivo',
            'revisada_por'
        ])
        messages.success(request, f'Supervisión retirada de la solicitud {solicitud.numero}.')
    else:
        # Marcar como revisada
        solicitud.revisada_directivo       = True
        solicitud.fecha_revision_directivo = timezone.now()
        solicitud.revisada_por             = request.user
        solicitud.save(update_fields=[
            'revisada_directivo',
            'fecha_revision_directivo',
            'revisada_por'
        ])
        messages.success(request, f'Solicitud {solicitud.numero} marcada como revisada por dirección.')

    # Respuesta AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok':               True,
            'revisada':         solicitud.revisada_directivo,
            'revisada_por':     solicitud.revisada_por.get_nombre_completo() if solicitud.revisada_por else '',
            'fecha_revision':   solicitud.fecha_revision_directivo.strftime('%d/%m/%Y %H:%M') if solicitud.fecha_revision_directivo else '',
        })

    return redirect('solicitudes:detalle', pk=pk)