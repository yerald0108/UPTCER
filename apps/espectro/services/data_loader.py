# apps/espectro/services/data_loader.py
from decimal import Decimal

from apps.espectro.models import FactorFrecuencia, FactorServicio, FactorK, IntensidadCampoE
from django.core.cache import cache
from django.db import models

def get_factor_frecuencia(frecuencia_mhz):
    """Obtiene f(t) según la banda de frecuencia."""
    cache_key = f'ft_{frecuencia_mhz}'
    valor = cache.get(cache_key)
    if valor is None:
        qs = FactorFrecuencia.objects.filter(
            banda_min__lte=frecuencia_mhz
        )
        # Si banda_max es None, significa "hasta infinito"; si no, filtramos por max
        qs = qs.filter(models.Q(banda_max__isnull=True) | models.Q(banda_max__gt=frecuencia_mhz))
        factor = qs.first()
        if factor:
            valor = factor.valor
        else:
            # fallback: el último registro (ej. > 300 GHz)
            factor = FactorFrecuencia.objects.last()
            valor = factor.valor if factor else Decimal(1)
        cache.set(cache_key, valor, 3600)
    return valor

def get_factor_servicio(grupo, subcategoria):
    cache_key = f'c_{grupo}_{subcategoria}'
    valor = cache.get(cache_key)
    if valor is None:
        factor = FactorServicio.objects.get(grupo=grupo, subcategoria=subcategoria)
        valor = factor.valor_c
        cache.set(cache_key, valor, 3600)
    return valor

def get_factor_k(modo_uso, naturaleza):
    cache_key = f'k_{modo_uso}_{naturaleza}'
    valor = cache.get(cache_key)
    if valor is None:
        factor = FactorK.objects.get(modo_uso=modo_uso, naturaleza=naturaleza)
        valor = factor.valor_k
        cache.set(cache_key, valor, 3600)
    return valor

def get_intensidad_campo(frecuencia_mhz):
    """Obtiene E (mV/m) para la frecuencia más cercana por debajo."""
    cache_key = f'e_{frecuencia_mhz}'
    valor = cache.get(cache_key)
    if valor is None:
        # Seleccionar el registro con frecuencia <= dada, orden descendente
        qs = IntensidadCampoE.objects.filter(frecuencia_mhz__lte=frecuencia_mhz).order_by('-frecuencia_mhz')
        registro = qs.first()
        if registro:
            valor = registro.valor_e_mv_m
        else:
            # Si no hay, tomar el primero (frecuencia más baja)
            registro = IntensidadCampoE.objects.first()
            valor = registro.valor_e_mv_m if registro else Decimal('0.1')
        cache.set(cache_key, valor, 3600)
    return valor