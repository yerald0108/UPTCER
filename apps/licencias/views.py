import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils import timezone
from .models import Licencia, Factura
from .servicios import registrar_pago
from django.db.models import Q


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
    hoy = timezone.now().date()

    if usuario.es_persona_natural:
        licencias = Licencia.objects.filter(
            solicitud__solicitante=usuario
        ).select_related('solicitud', 'emitida_por')
    else:
        licencias = Licencia.objects.select_related(
            'solicitud', 'emitida_por', 'solicitud__solicitante'
        ).all()

    # Actualizar vencimientos
    licencias.filter(
        estado=Licencia.ESTADO_VIGENTE,
        fecha_vencimiento__lt=hoy
    ).update(estado=Licencia.ESTADO_VENCIDA)

    estado = request.GET.get('estado', '')
    if estado:
        licencias = licencias.filter(estado=estado)

    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    if fecha_desde:
        licencias = licencias.filter(fecha_emision__date__gte=fecha_desde)
    if fecha_hasta:
        licencias = licencias.filter(fecha_emision__date__lte=fecha_hasta)

    busqueda = request.GET.get('q', '')
    if busqueda:
        licencias = licencias.filter(
            Q(numero__icontains=busqueda) |
            Q(solicitud__numero__icontains=busqueda) |
            Q(solicitud__solicitante__nombre__icontains=busqueda) |
            Q(solicitud__solicitante__apellidos__icontains=busqueda)
        )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'licencias/tabla_licencias.html', {
            'licencias':     licencias,
            'estado_actual': estado,
            'fecha_desde':   fecha_desde,
            'fecha_hasta':   fecha_hasta,
            'busqueda':      busqueda,
        })

    return render(request, 'licencias/lista.html', {
        'licencias':     licencias,
        'estado_actual': estado,
        'fecha_desde':   fecha_desde,
        'fecha_hasta':   fecha_hasta,
        'busqueda':      busqueda,
        'ESTADOS':       Licencia.ESTADOS,
    })


@never_cache
@login_required
def revocar_licencia(request, numero):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para revocar licencias.')
        return redirect('licencias:lista')

    licencia = get_object_or_404(Licencia, numero=numero)

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, 'Debe especificar el motivo de revocación.')
            return redirect('licencias:detalle', numero=numero)

        licencia.estado            = Licencia.ESTADO_REVOCADA
        licencia.motivo_revocacion = motivo
        licencia.fecha_revocacion  = timezone.now()
        licencia.save()

        messages.success(request, f'Licencia {licencia.numero} revocada correctamente.')
        return redirect('licencias:detalle', numero=numero)

    return redirect('licencias:detalle', numero=numero)


# ─── Detalle de factura ───────────────────────────────────────────────────────
@never_cache
@login_required
def detalle_factura(request, numero):
    factura   = get_object_or_404(Factura, numero=numero)
    usuario   = request.user
    solicitud = factura.solicitud

    if usuario.es_persona_natural and solicitud.solicitante != usuario:
        messages.error(request, 'No tiene permisos para ver esta factura.')
        return redirect('solicitudes:mis_solicitudes')

    datos_f43 = {}
    equipos   = []
    try:
        datos_f43 = json.loads(solicitud.equipo_descripcion or '{}')
        equipos   = datos_f43.get('equipos', [])
    except (json.JSONDecodeError, TypeError):
        pass

    return render(request, 'licencias/detalle_factura.html', {
        'factura':   factura,
        'solicitud': solicitud,
        'datos_f43': datos_f43,
        'equipos':   equipos,
    })


# ─── Lista de facturas ────────────────────────────────────────────────────────
@never_cache
@login_required
def lista_facturas(request):
    usuario = request.user

    if usuario.es_persona_natural:
        facturas = Factura.objects.filter(
            solicitud__solicitante=usuario
        ).select_related('solicitud', 'emitida_por')
    else:
        facturas = Factura.objects.select_related(
            'solicitud', 'emitida_por', 'solicitud__solicitante'
        ).all()

    estado = request.GET.get('estado', '')
    if estado:
        facturas = facturas.filter(estado=estado)

    busqueda = request.GET.get('q', '')
    if busqueda:
        facturas = facturas.filter(
            Q(numero__icontains=busqueda) |
            Q(solicitud__numero__icontains=busqueda) |
            Q(solicitud__solicitante__nombre__icontains=busqueda) |
            Q(solicitud__solicitante__apellidos__icontains=busqueda)
        )

    return render(request, 'licencias/lista_facturas.html', {
        'facturas':      facturas,
        'estado_actual': estado,
        'busqueda':      busqueda,
        'ESTADOS':       Factura.ESTADOS,
    })


# ─── Registrar pago de factura ────────────────────────────────────────────────
@never_cache
@login_required
def registrar_pago_factura(request, numero):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para registrar pagos.')
        return redirect('licencias:lista_facturas')

    factura = get_object_or_404(Factura, numero=numero)

    if factura.esta_pagada:
        messages.error(request, 'Esta factura ya fue pagada.')
        return redirect('licencias:detalle_factura', numero=numero)

    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '').strip()
        factura.observaciones = observaciones
        factura.save(update_fields=['observaciones'])

        registrar_pago(factura, request.user)

        messages.success(
            request,
            f'Pago registrado correctamente. La licencia ha sido generada.'
        )
        return redirect('licencias:detalle_factura', numero=numero)

    return redirect('licencias:detalle_factura', numero=numero)