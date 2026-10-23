# apps/espectro/services/calculator.py
import math
from decimal import Decimal

def calcular_banda_estandar(fi, ff):
    """B = Ff - Fi (MHz)"""
    return ff - fi

def calcular_banda_satelital(velocidad_mbps, modulacion):
    """B = (1.5 * V) / ln(M)"""
    tabla_m = {'MQPSK': 4, '8PSK': 8, '16APSK': 16, '32APSK': 32}
    m = tabla_m.get(modulacion.upper(), 4)
    if m <= 1:
        raise ValueError("M debe ser > 1")
    return (1.5 * velocidad_mbps) / math.log(m)

def calcular_distancia_d(fc, htx, hrx, pt_dbm, gax_dbi, lt_constante, diff):
    """
    Calcula d (km) según fórmula de Okumura-Hata adaptada.
    fc: MHz, htx/hrx: metros, pt_dbm: dBm, gax_dbi: dBi
    lt_constante: 56 (FM), 65 (TV analógica), 70 (TV digital), etc.
    diff: factor de corrección por ubicación (ej. 0 para microceldas)
    """
    lt = pt_dbm + gax_dbi + lt_constante
    if fc <= 1500:
        num = (69.55 + 26.16 * math.log10(fc)
               - 13.82 * math.log10(htx)
               - (1.1 * math.log10(fc) - 0.7) * hrx
               - (1.56 * math.log10(fc) - 0.8)
               - lt + diff)
    else:
        num = (46.3 + 33.9 * math.log10(fc)
               - 13.82 * math.log10(htx)
               - (1.1 * math.log10(fc) - 0.7) * hrx
               - (1.56 * math.log10(fc) - 0.8)
               - lt + diff)
    den = 44.9 - 6.55 * math.log10(htx)
    x = num / den
    return 10 ** x

def calcular_area(d, alfa_grados, es_satelital=False):
    """
    A = pi * d^2 * (alfa / 360)  o (alfa/180) para satelital
    d en km, alfa en grados
    """
    if es_satelital:
        return math.pi * (d ** 2) * (alfa_grados / 180.0)
    return math.pi * (d ** 2) * (alfa_grados / 360.0)

def calcular_valor_espectro(ancho_banda_mhz, area_km2, factor_frecuencia,
                            factor_k, tiempo_anios, factor_servicio_c,
                            grupo):
    """
    V = B * A * f(t) * k * T * c * x  (x=1 o w=1)
    grupo: '1' para CUP, '2' para USD
    Devuelve Decimal con el valor mínimo aplicado.
    """
    resultado = (Decimal(str(ancho_banda_mhz)) *
                 Decimal(str(area_km2)) *
                 Decimal(str(factor_frecuencia)) *
                 Decimal(str(factor_k)) *
                 Decimal(str(tiempo_anios)) *
                 Decimal(str(factor_servicio_c)))
    if grupo == '1' and resultado < 60:
        resultado = Decimal(60)
    elif grupo == '2' and resultado < 12:
        resultado = Decimal(12)
    return resultado