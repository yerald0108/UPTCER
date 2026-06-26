import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils import timezone
from .models import Licencia


@never_cache
@login_required
def detalle_licencia(request, numero):
    licencia  = get_object_or_404(Licencia, numero=numero)
    usuario   = request.user
    solicitud = licencia.solicitud

    licencia.verificar_vencimiento()

    if usuario.es_persona_natural and solicitud.solicitante != usuario:
        messages.error(request, 'No tiene permisos para ver esta licencia.')
        return redirect('solicitudes:mis_solicitudes')

    # Parsear datos F43
    datos_f43 = {}
    equipos   = []
    try:
        datos_f43 = json.loads(solicitud.equipo_descripcion or '{}')
        equipos   = datos_f43.get('equipos', [])
    except (json.JSONDecodeError, TypeError):
        pass

    return render(request, 'licencias/detalle.html', {
        'licencia':  licencia,
        'solicitud': solicitud,
        'datos_f43': datos_f43,
        'equipos':   equipos,
    })


@never_cache
@login_required
def lista_licencias(request):
    usuario = request.user

    if usuario.es_persona_natural:
        licencias = Licencia.objects.filter(
            solicitud__solicitante=usuario
        ).select_related('solicitud', 'emitida_por')
    else:
        licencias = Licencia.objects.select_related(
            'solicitud', 'emitida_por', 'solicitud__solicitante'
        ).all()

    for lic in licencias:
        lic.verificar_vencimiento()

    estado = request.GET.get('estado', '')
    if estado:
        licencias = licencias.filter(estado=estado)

    return render(request, 'licencias/lista.html', {
        'licencias':     licencias,
        'estado_actual': estado,
        'ESTADOS':       Licencia.ESTADOS,
    })


@never_cache
@login_required
def revocar_licencia(request, numero):
    if not (request.user.es_operador or request.user.es_directivo):
        messages.error(request, 'No tiene permisos para revocar licencias.')
        return redirect('licencias:lista')

    licencia = get_object_or_404(Licencia, numero=numero)

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, 'Debe especificar el motivo de revocación.')
            return redirect('licencias:detalle', numero=numero)

        licencia.estado             = Licencia.ESTADO_REVOCADA
        licencia.motivo_revocacion  = motivo
        licencia.fecha_revocacion   = timezone.now()
        licencia.save()

        messages.success(request, f'Licencia {licencia.numero} revocada correctamente.')
        return redirect('licencias:detalle', numero=numero)

    return redirect('licencias:detalle', numero=numero)