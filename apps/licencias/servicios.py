from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from .models import Licencia


def generar_licencia(solicitud, emitida_por):
    """
    Genera automáticamente una licencia cuando una solicitud es aprobada.
    Si ya existe una licencia para esta solicitud, la retorna sin crear otra.
    """
    if hasattr(solicitud, 'licencia'):
        return solicitud.licencia

    import json
    fecha_vencimiento = None

    # Calcular fecha de vencimiento si es importación temporal
    try:
        datos = json.loads(solicitud.equipo_descripcion or '{}')
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