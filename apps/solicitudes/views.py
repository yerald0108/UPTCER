import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils import timezone
from .models import Solicitud, HistorialSolicitud
from .forms import FormularioF43
from apps.notificaciones.servicios import (
    notificar_solicitud_nueva,
    notificar_cambio_estado,
    notificar_derivacion_especialista,
    notificar_criterio_tecnico,
)


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
    solicitudes = Solicitud.objects.filter(
        solicitante=request.user
    ).order_by('-fecha_creacion')

    return render(request, 'solicitudes/mis_solicitudes.html', {
        'solicitudes': solicitudes,
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
        from apps.licencias.servicios import generar_licencia
        generar_licencia(solicitud, usuario)

    messages.success(
        request,
        f'Estado de la solicitud {solicitud.numero} actualizado a "{solicitud.get_estado_display()}".'
    )
    return redirect('solicitudes:detalle', pk=pk)


# ─── Lista de solicitudes (operador/directivo) ────────────────────────────────
@never_cache
@login_required
def lista_solicitudes(request):
    usuario = request.user

    if not (usuario.es_operador or usuario.es_directivo or usuario.es_especialista):
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    solicitudes = Solicitud.objects.select_related(
        'solicitante', 'operador_asignado'
    ).order_by('-fecha_creacion')

    # Filtros
    estado = request.GET.get('estado', '')
    flujo  = request.GET.get('flujo', '')

    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    if flujo:
        solicitudes = solicitudes.filter(flujo=flujo)

    return render(request, 'solicitudes/lista.html', {
        'solicitudes': solicitudes,
        'estado_actual': estado,
        'flujo_actual':  flujo,
        'ESTADOS': Solicitud.ESTADOS,
        'FLUJOS':  Solicitud.FLUJOS,
    })