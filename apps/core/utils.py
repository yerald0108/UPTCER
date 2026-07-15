from django.db import models
from django.utils import timezone


def generar_numero_secuencial(queryset, prefijo, ancho=4, campo='numero'):
    """
    Genera un número secuencial basado en el prefijo y año actual,
    con protección contra condiciones de carrera mediante select_for_update().

    Args:
        queryset: QuerySet del modelo donde buscar (ej. Solicitud.objects)
        prefijo: Prefijo del número (ej. 'F43', 'RAT', 'LIC')
        ancho: Ancho del número secuencial con zfill (default 4)
        campo: Nombre del campo donde buscar el máximo (default 'numero')

    Returns:
        str: Número generado (ej. 'F43-2026-0001')
    """
    año = timezone.now().year
    prefijo_completo = f'{prefijo}-{año}'

    ultimo = queryset.select_for_update().filter(
        **{f'{campo}__startswith': prefijo_completo}
    ).aggregate(max_num=models.Max(campo))['max_num']

    if ultimo:
        seq = int(ultimo.split('-')[-1]) + 1
    else:
        seq = 1

    return f'{prefijo_completo}-{str(seq).zfill(ancho)}'