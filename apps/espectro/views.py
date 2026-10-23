from django.shortcuts import render
from decimal import Decimal
import logging

from .forms import CalculoEspectroForm
from .services.calculator import (
    calcular_banda_estandar,
    calcular_banda_satelital,
    calcular_distancia_d,
    calcular_area,
    calcular_valor_espectro,
)
from .services.data_loader import (
    get_factor_frecuencia,
    get_factor_servicio,
    get_factor_k,
)

logger = logging.getLogger(__name__)


# ============================================================
# VISTAS DE CÁLCULO
# ============================================================

def seleccion_anexo_view(request):
    """Pantalla de bienvenida: dos cards, una por anexo."""
    return render(request, 'espectro/seleccion_anexo.html')


def calcular_view(request, grupo='1'):
    """
    Formulario de cálculo. El grupo viene de la URL ('1' o '2').
    """
    if grupo not in ('1', '2'):
        grupo = '1'

    resultado = None

    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['grupo'] = grupo
        form = CalculoEspectroForm(post_data, initial={'grupo': grupo})

        if form.is_valid():
            try:
                data = form.cleaned_data

                servicio_subcategoria = data['servicio']
                fc = data['fc']
                htx = data['htx']
                hrx = data['hrx']
                pt = data['pt']
                gax = data['gax']
                lt_const = data['lt_constante']
                diff = data['diff']
                tiempo = data['tiempo_anios']
                modo = data['modo_uso']
                naturaleza = data['naturaleza']
                metodo_b = data['metodo_b']
                metodo_a = data['metodo_a']

                # Calcular B
                if metodo_b == 'estandar':
                    B = calcular_banda_estandar(data['fi'], data['ff'])
                else:
                    B = calcular_banda_satelital(data['velocidad_mbps'], data['modulacion'])

                # Calcular A
                d_calc = None
                if metodo_a == 'directa':
                    A = data['area_directa']
                elif metodo_a == 'd_alfa':
                    d = data['d']
                    alfa = data['alfa']
                    es_satelital = data.get('es_satelital_area', False)
                    A = calcular_area(d, alfa, es_satelital)
                else:
                    d_calc = calcular_distancia_d(fc, htx, hrx, pt, gax, lt_const, diff)
                    A = calcular_area(d_calc, 360.0, False)

                limite_territorio = 109884.01
                if A > limite_territorio:
                    A = limite_territorio
                if A < 1:
                    A = 1.0

                # Factores
                ft = get_factor_frecuencia(fc)
                c = get_factor_servicio(grupo, servicio_subcategoria)
                k = get_factor_k(modo, naturaleza)

                # Valor
                V = calcular_valor_espectro(B, A, ft, k, tiempo, c, grupo)

                resultado = {
                    'B': B,
                    'A': A,
                    'ft': ft,
                    'k': k,
                    'c': c,
                    'T': tiempo,
                    'V': V,
                    'moneda': 'CUP' if grupo == '1' else 'USD',
                    'metodo_b': metodo_b,
                    'metodo_a': metodo_a,
                    'servicio': servicio_subcategoria,
                    'fc': fc,
                    'htx': htx,
                    'hrx': hrx,
                    'pt': pt,
                    'gax': gax,
                    'lt_const': lt_const,
                    'diff': diff,
                }
                if d_calc is not None:
                    resultado['d_calculada'] = d_calc

            except Exception as e:
                logger.error(f"Error en cálculo: {str(e)}")
                form.add_error(None, f"Error en el cálculo: {str(e)}")
                resultado = None
    else:
        form = CalculoEspectroForm(initial={'grupo': grupo})

    contexto = {
        'form': form,
        'resultado': resultado,
        'grupo': grupo,
        'nombre_anexo': 'ANEXO I — Grupo 1 (CUP)' if grupo == '1'
                        else 'ANEXO II — Grupo 2 (USD)',
        'descripcion_grupo': (
            'Órganos, organismos, entidades nacionales, empresas mixtas, '
            'formas de gestión no estatal y personas naturales residentes.'
            if grupo == '1' else
            'Personas jurídicas extranjeras, personas naturales extranjeras '
            'no residentes, misiones diplomáticas y organismos internacionales.'
        ),
    }
    return render(request, 'espectro/calculo.html', contexto)