from datetime import date
from dateutil.relativedelta import relativedelta
from .models import Licencia, Factura
from django.utils import timezone
import json


def generar_factura(solicitud, emitida_por):
    """
    Genera una factura cuando el directivo aprueba la solicitud.
    Si ya existe una factura para esta solicitud, la retorna sin crear otra.
    El módulo de cálculo de montos se integrará más adelante.
    """
    try:
        return solicitud.factura
    except Factura.DoesNotExist:
        pass

    factura = Factura.objects.create(
        solicitud   = solicitud,
        emitida_por = emitida_por,
        subtotal    = 0,
        impuesto    = 0,
        total       = 0,
    )

    return factura


def registrar_pago(factura, usuario):
    """
    Registra el pago de una factura y genera la licencia automáticamente.
    """
    if factura.esta_pagada:
        return factura

    factura.estado              = Factura.ESTADO_PAGADA
    factura.fecha_pago          = timezone.now()
    factura.registrado_pago_por = usuario
    factura.save()

    # Al pagarse la factura se genera la licencia
    generar_licencia(factura.solicitud, usuario)

    return factura


def generar_licencia(solicitud, emitida_por):
    """
    Genera la licencia imprimible cuando la factura está pagada.
    Si ya existe una licencia para esta solicitud, la retorna sin crear otra.
    """
    try:
        return solicitud.licencia
    except Licencia.DoesNotExist:
        pass

    fecha_vencimiento = None

    # Calcular fecha de vencimiento si es importación temporal
    try:
        datos  = json.loads(solicitud.equipo_descripcion or '{}')
        periodo = datos.get('periodo_importacion', 'definitiva')
        meses   = int(datos.get('tiempo_solicitado') or 0)
        if periodo == 'temporal' and meses > 0:
            fecha_vencimiento = date.today() + relativedelta(months=meses)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    licencia = Licencia.objects.create(
        solicitud         = solicitud,
        emitida_por       = emitida_por,
        fecha_vencimiento = fecha_vencimiento,
    )

    return licencia