from io import StringIO
from decimal import Decimal

from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import Usuario
from apps.espectro.models import FactorK, FactorServicio
from apps.espectro.services.data_loader import (
    get_factor_frecuencia,
    get_intensidad_campo,
)


class EspectroUrlTest(TestCase):

    def setUp(self):
        self.directivo = Usuario.objects.create_user(
            username='espectro_directivo',
            email='espectro_directivo@uptcer.cu',
            nombre='Directivo',
            apellidos='Espectro',
            rol=Usuario.ROL_DIRECTIVO,
            password='test1234',
        )
        self.client.force_login(self.directivo)

    def test_seleccion_anexo_usa_ruta_del_proyecto(self):
        self.assertEqual(reverse('espectro:seleccion_anexo'), '/espectro/')

    def test_seleccion_anexo_carga(self):
        response = self.client.get(reverse('espectro:seleccion_anexo'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'espectro/seleccion_anexo.html')
        self.assertTemplateUsed(response, 'base/base.html')
        self.assertContains(response, 'class="layout-sidebar"')
        self.assertContains(response, 'data-tooltip="Espectro"')
        self.assertContains(response, 'class="sidebar-enlace activo" data-tooltip="Espectro"')

    def test_pantalla_calculo_se_muestra_dentro_del_panel(self):
        response = self.client.get(reverse('espectro:calcular', args=['1']))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'espectro/calculo.html')
        self.assertTemplateUsed(response, 'base/base.html')
        self.assertContains(response, 'id="calculoForm"')
        self.assertContains(response, 'data-tooltip="Espectro"')

    def test_comando_poblacion_carga_servicios_de_espectro(self):
        call_command('poblar_datos', stdout=StringIO())

        self.assertTrue(FactorServicio.objects.filter(grupo='1').exists())
        self.assertTrue(FactorServicio.objects.filter(grupo='2').exists())
        self.assertTrue(FactorServicio.objects.filter(
            grupo='1',
            subcategoria='Fijo punto a punto - Monocanales',
            valor_c=8,
        ).exists())
        self.assertTrue(FactorServicio.objects.filter(
            grupo='2',
            subcategoria='Fijo punto a punto - Radioenlaces < 800 MHz',
            valor_c='0.146',
        ).exists())
        self.assertEqual(
            FactorK.objects.get(
                modo_uso='COMPARTIDO',
                naturaleza='COMERCIAL',
            ).valor_k,
            Decimal('1.00'),
        )

        response = self.client.post(
            reverse('espectro:calcular', args=['1']),
            {
                'servicio': 'Fijo punto a punto - Monocanales',
                'fc': '900',
                'htx': '30',
                'hrx': '1.5',
                'pt': '40',
                'gax': '10',
                'lt_constante': '65',
                'diff': '0',
                'metodo_b': 'estandar',
                'fi': '700',
                'ff': '800',
                'metodo_a': 'directa',
                'area_directa': '1',
                'modo_uso': 'COMPARTIDO',
                'naturaleza': 'COMERCIAL',
                'tiempo_anios': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['resultado'])


class EspectroDataLoaderTest(TestCase):

    def setUp(self):
        cache.clear()

    def test_factor_frecuencia_usa_respaldo_decimal_sin_registros(self):
        self.assertEqual(get_factor_frecuencia(900), Decimal(1))

    def test_intensidad_campo_usa_respaldo_decimal_sin_registros(self):
        self.assertEqual(get_intensidad_campo(900), Decimal('0.1'))
