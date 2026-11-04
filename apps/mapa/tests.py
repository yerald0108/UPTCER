import io
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import TestCase, override_settings
from django.urls import reverse
from apps.accounts.models import Usuario
from apps.licencias.models import Licencia
from apps.mapa.models import PuntoMapa
from apps.mapa.services.satelites import (
    DatosOrbitalesNoDisponibles,
    _parsear_tle,
    _posicion_geografica,
    cargar_elementos_orbitales,
    obtener_trayectorias_satelitales,
)
from apps.solicitudes.models import Solicitud


TLE_PRUEBA = (
    'VANGUARD 1\n'
    '1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753\n'
    '2 00005  34.2682 331.5174 1849677 331.7664  19.3264 10.82419157413667\n'
)


class MapaViewTest(TestCase):

    def setUp(self):
        self.directivo = Usuario.objects.create_user(
            username='mapa_directivo',
            email='mapa_directivo@uptcer.cu',
            nombre='Directivo',
            apellidos='Mapa',
            rol=Usuario.ROL_DIRECTIVO,
            password='test1234',
        )
        self.directivo.is_staff = True
        self.directivo.save(update_fields=['is_staff'])
        self.client.force_login(self.directivo)

    def test_vista_principal_del_mapa(self):
        response = self.client.get(reverse('mapa:mapa'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mapa/mapa.html')
        self.assertContains(response, '/static/mapa/vendor/maplibre-gl.css')
        self.assertContains(response, 'Mapa de instalaciones y cobertura')
        self.assertContains(response, 'mapa-provincia')
        self.assertContains(response, 'mapa-municipio')
        self.assertContains(response, 'mapa-frecuencia-desde')
        self.assertContains(response, 'mapa-frecuencia-hasta')
        self.assertContains(response, 'mapa-filtro-satelite')
        self.assertContains(response, 'Todos los satélites')
        self.assertContains(response, 'id="mapa-controles"')
        self.assertContains(response, 'Configuración y filtros del mapa')
        self.assertContains(response, '/static/mapa/js/mapa-directivo.js')
        self.assertContains(response, 'Trayectorias y huellas satelitales')
        self.assertContains(response, reverse('mapa:api_satelites'))
        self.assertContains(response, '/static/mapa/data/cuba_municipios.geojson')
        self.assertNotContains(response, 'unpkg.com/maplibre')

    def test_mapa_regular_conserva_su_vista(self):
        usuario = Usuario.objects.create_user(
            username='mapa_regular',
            email='mapa_regular@uptcer.cu',
            nombre='Usuario',
            apellidos='Regular',
            rol=Usuario.ROL_ESPECIALISTA_MOVIL,
            password='test1234',
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse('mapa:mapa'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/static/mapa/js/mapa.js')
        self.assertNotContains(response, 'mapa-frecuencia-desde')

    def test_mapa_exige_autenticacion(self):
        self.client.logout()
        response = self.client.get(reverse('mapa:mapa'))

        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("mapa:mapa")}',
        )

    def test_selector_de_ubicacion_muestra_mapa_y_busqueda(self):
        response = self.client.get(
            reverse('mapa:seleccionar_ubicacion'),
            {'q': 'Calle 1, La Habana'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mapa/seleccionar_ubicacion.html')
        self.assertContains(response, 'Buscar dirección')
        self.assertContains(response, 'Usar esta ubicación')
        self.assertContains(response, '/static/mapa/vendor/maplibre-gl.css')
        self.assertContains(response, '/static/mapa/js/mapa-selector.js')
        self.assertNotContains(response, 'unpkg.com/maplibre')

    def test_pmtiles_soporta_solicitudes_http_de_rango(self):
        response = self.client.get(
            reverse('mapa:pmtiles'),
            HTTP_RANGE='bytes=0-31',
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Range'].split('/')[0], 'bytes 0-31')
        self.assertEqual(response['Content-Length'], '32')
        self.assertEqual(len(b''.join(response.streaming_content)), 32)

    def test_pmtiles_rechaza_rango_fuera_del_archivo(self):
        response = self.client.get(
            reverse('mapa:pmtiles'),
            HTTP_RANGE='bytes=999999999-',
        )

        self.assertEqual(response.status_code, 416)
        self.assertIn('bytes */', response['Content-Range'])

    def test_selector_de_ubicacion_no_exige_inicio_de_sesion(self):
        self.client.logout()

        response = self.client.get(reverse('mapa:seleccionar_ubicacion'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mapa/seleccionar_ubicacion.html')

    def test_crear_punto_requiere_cuenta_de_personal_admin(self):
        usuario = Usuario.objects.create_user(
            username='mapa_usuario',
            email='mapa_usuario@uptcer.cu',
            nombre='Usuario',
            apellidos='Normal',
            rol=Usuario.ROL_DIRECTIVO,
            password='test1234',
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse('mapa:crear_punto'))

        self.assertRedirects(
            response,
            f'{reverse("admin:login")}?next={reverse("mapa:crear_punto")}',
        )

    def test_api_crear_punto_no_permite_usuario_sin_acceso_admin(self):
        usuario = Usuario.objects.create_user(
            username='mapa_usuario_api',
            email='mapa_usuario_api@uptcer.cu',
            nombre='Usuario',
            apellidos='Normal',
            rol=Usuario.ROL_DIRECTIVO,
            password='test1234',
        )
        self.client.force_login(usuario)

        response = self.client.post(
            reverse('mapa:api_crear_punto'),
            {'nombre': 'Punto no autorizado', 'latitud': 23, 'longitud': -82},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response['Location'])
        self.assertFalse(PuntoMapa.objects.filter(nombre='Punto no autorizado').exists())

    def test_api_crear_punto_valida_radio_de_cobertura(self):
        response = self.client.post(
            reverse('mapa:api_crear_punto'),
            data={
                'nombre': 'Punto con radio inválido',
                'latitud': 23,
                'longitud': -82,
                'atributos': {'radio_km': 0},
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('radio', response.json()['error'])
        self.assertFalse(PuntoMapa.objects.filter(nombre='Punto con radio inválido').exists())

    def test_api_crear_punto_guarda_radio_y_frecuencia(self):
        response = self.client.post(
            reverse('mapa:api_crear_punto'),
            data={
                'nombre': 'Punto con cobertura',
                'latitud': 23,
                'longitud': -82,
                'atributos': {'radio_km': '2.5', 'frecuencia_mhz': '2450'},
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['punto']['properties']['radio_km'], 2.5)
        self.assertEqual(response.json()['punto']['properties']['frecuencia_mhz'], 2450)

    def test_formulario_admin_expone_y_persiste_radio_y_frecuencia(self):
        self.directivo.is_superuser = True
        self.directivo.save(update_fields=['is_superuser'])
        response = self.client.post(
            reverse('admin:mapa_puntomapa_add'),
            {
                'nombre': 'Punto admin con cobertura',
                'tipo': 'ESTACION_BASE',
                'estado': 'ACTIVO',
                'latitud': 23,
                'longitud': -82,
                'frecuencia_mhz': '900',
                'radio_km': '4',
            },
        )

        self.assertEqual(response.status_code, 302)
        punto = PuntoMapa.objects.get(nombre='Punto admin con cobertura')
        self.assertEqual(punto.atributos['frecuencia_mhz'], 900)
        self.assertEqual(punto.atributos['radio_km'], 4)

    def test_mapa_regresa_a_la_ruta_interna_indicada(self):
        response = self.client.get(
            reverse('mapa:mapa'),
            {'next': reverse('accounts:dashboard')},
        )

        self.assertContains(response, f'href="{reverse("accounts:dashboard")}"')

    def test_mapa_rechaza_ruta_de_regreso_externa(self):
        response = self.client.get(
            reverse('mapa:mapa'),
            {'next': 'https://example.com'},
        )

        self.assertContains(response, f'href="{reverse("accounts:dashboard")}"')

    def test_api_muestra_dispositivo_y_licencia_de_la_solicitud(self):
        solicitante = Usuario.objects.create_user(
            username='mapa_solicitante',
            email='mapa_solicitante@uptcer.cu',
            nombre='Ana',
            apellidos='Solicitante',
            rol=Usuario.ROL_PERSONA_NATURAL,
            password='test1234',
        )
        solicitud = Solicitud.objects.create(
            flujo=Solicitud.FLUJO_F43,
            categoria=Solicitud.CATEGORIA_MOVIL,
            estado=Solicitud.ESTADO_APROBADA,
            solicitante=solicitante,
            direccion_instalacion='Calle 1, La Habana',
            latitud_instalacion=23.1136,
            longitud_instalacion=-82.3666,
            equipo_descripcion=(
                '{"equipos":[{"descripcion":"Teléfono","marca":"Samsung",'
                '"modelo":"Galaxy S24"}]}'
            ),
        )
        licencia = Licencia.objects.create(
            solicitud=solicitud,
            emitida_por=self.directivo,
        )
        PuntoMapa.objects.create(
            nombre=solicitud.numero,
            solicitud=solicitud,
            tipo='ESTACION_MOVIL',
            estado='ACTIVO',
            latitud=solicitud.latitud_instalacion,
            longitud=solicitud.longitud_instalacion,
            direccion=solicitud.direccion_instalacion,
            atributos={
                'equipos': [{'descripcion': 'Teléfono'}],
                'frecuencia_mhz': 2450,
                'radio_km': 2.5,
            },
        )

        response = self.client.get(reverse('mapa:api_puntos'))
        properties = response.json()['features'][0]['properties']

        self.assertEqual(properties['licencia_numero'], licencia.numero)
        self.assertEqual(properties['solicitante'], 'Ana Solicitante')
        self.assertEqual(properties['direccion_instalacion'], 'Calle 1, La Habana')
        self.assertEqual(properties['frecuencia_mhz'], 2450)
        self.assertEqual(properties['radio_km'], 2.5)

    @patch('apps.mapa.views.obtener_trayectorias_satelitales')
    def test_api_satelites_devuelve_trayectorias(self, obtener_trayectorias):
        resultado = {
            'type': 'FeatureCollection',
            'features': [],
            'satelites_sobre_cuba': 0,
        }
        obtener_trayectorias.return_value = resultado

        response = self.client.get(reverse('mapa:api_satelites'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), resultado)

    @patch(
        'apps.mapa.views.obtener_trayectorias_satelitales',
        side_effect=DatosOrbitalesNoDisponibles('No hay TLE.'),
    )
    def test_api_satelites_informa_si_no_hay_datos_orbitales(self, obtener_trayectorias):
        response = self.client.get(reverse('mapa:api_satelites'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'No hay TLE.')

    def test_api_satelites_exige_autenticacion(self):
        self.client.logout()

        response = self.client.get(reverse('mapa:api_satelites'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])


class SatelliteTrackingServiceTest(TestCase):

    def test_fuente_sin_cache_usa_alternativa_y_advierte_cobertura_parcial(self):
        with TemporaryDirectory() as directorio:
            with override_settings(MEDIA_ROOT=directorio):
                with patch(
                    'apps.mapa.services.satelites.urlopen',
                    side_effect=[
                        HTTPError('https://celestrak.org', 403, 'rate limited', None, io.BytesIO()),
                        io.BytesIO(TLE_PRUEBA.encode('utf-8')),
                    ],
                ) as descargar:
                    satelites, fecha, aviso, fuente = cargar_elementos_orbitales()

                ruta = Path(directorio) / 'datos_satelites' / 'activos.tle'
                self.assertTrue(ruta.is_file())
                self.assertTrue(ruta.with_suffix('.attempt').is_file())
                self.assertEqual(len(satelites), 1)
                self.assertIsNotNone(fecha)
                self.assertIn('parcial', aviso)
                self.assertIn('subset', fuente)
                self.assertEqual(descargar.call_count, 2)

    def test_fuente_alternativa_no_espera_el_intervalo_del_intento_anterior(self):
        with TemporaryDirectory() as directorio:
            with override_settings(MEDIA_ROOT=directorio):
                ruta = Path(directorio) / 'datos_satelites' / 'activos.attempt'
                ruta.parent.mkdir(parents=True)
                ruta.write_text('intento anterior', encoding='utf-8')

                with patch(
                    'apps.mapa.services.satelites.urlopen',
                    return_value=io.BytesIO(TLE_PRUEBA.encode('utf-8')),
                ) as descargar:
                    satelites, _, aviso, fuente = cargar_elementos_orbitales()

                self.assertEqual(len(satelites), 1)
                self.assertIn('parcial', aviso)
                self.assertIn('subset', fuente)
                descargar.assert_called_once()

    def test_fuentes_sin_cache_informa_si_no_hay_descargas_disponibles(self):
        error_activos = HTTPError(
            'https://celestrak.org', 403, 'rate limited', None, io.BytesIO()
        )
        error_alternativas = [
            URLError('visual sin conexión'),
            URLError('AMSAT sin conexión'),
        ]
        with TemporaryDirectory() as directorio:
            with override_settings(MEDIA_ROOT=directorio):
                with patch(
                    'apps.mapa.services.satelites.urlopen',
                    side_effect=[error_activos, *error_alternativas],
                ):
                    with self.assertRaisesRegex(
                        DatosOrbitalesNoDisponibles,
                        'fuente principal y las alternativas no están disponibles',
                    ):
                        cargar_elementos_orbitales()

                self.assertTrue(
                    (Path(directorio) / 'datos_satelites' / 'activos.attempt').is_file()
                )

    def test_elementos_orbitales_guardan_cache_descargado(self):
        with TemporaryDirectory() as directorio:
            with override_settings(MEDIA_ROOT=directorio):
                with patch(
                    'apps.mapa.services.satelites.urlopen',
                    return_value=io.BytesIO(TLE_PRUEBA.encode('utf-8')),
                ):
                    satelites, fecha, aviso, fuente = cargar_elementos_orbitales()

                ruta = Path(directorio) / 'datos_satelites' / 'activos.tle'
                self.assertTrue(ruta.is_file())
                self.assertEqual(len(satelites), 1)
                self.assertEqual(satelites[0][0], 'VANGUARD 1')
                self.assertIsNotNone(fecha)
                self.assertEqual(aviso, '')
                self.assertEqual(fuente, 'CelesTrak active')

    def test_elementos_orbitales_usan_cache_sin_conexion(self):
        with TemporaryDirectory() as directorio:
            with override_settings(MEDIA_ROOT=directorio):
                ruta = Path(directorio) / 'datos_satelites' / 'activos.tle'
                ruta.parent.mkdir(parents=True)
                ruta.write_text(TLE_PRUEBA, encoding='utf-8')
                fecha_antigua = (datetime.now(timezone.utc) - timedelta(hours=8)).timestamp()
                os.utime(ruta, (fecha_antigua, fecha_antigua))

                with patch(
                    'apps.mapa.services.satelites.urlopen',
                    side_effect=URLError('sin conexión'),
                ) as descargar:
                    satelites, fecha, aviso, fuente = cargar_elementos_orbitales()
                    _, _, segundo_aviso, _ = cargar_elementos_orbitales()

                self.assertEqual(len(satelites), 1)
                self.assertIsNotNone(fecha)
                self.assertIn('últimos datos guardados', aviso)
                self.assertIn('vencidos', segundo_aviso)
                self.assertEqual(fuente, 'Fuente orbital guardada')
                descargar.assert_called_once()

    def test_trayectorias_se_calculan_desde_tle_guardados(self):
        with TemporaryDirectory() as directorio:
            with override_settings(MEDIA_ROOT=directorio):
                ruta = Path(directorio) / 'datos_satelites' / 'activos.tle'
                ruta.parent.mkdir(parents=True)
                ruta.write_text(TLE_PRUEBA, encoding='utf-8')
                ruta.with_suffix('.source').write_text(
                    'CelesTrak visual (subset)',
                    encoding='utf-8',
                )
                with patch(
                    'apps.mapa.services.satelites._posicion_geografica',
                    return_value=(-79.0, 22.0, 500.0),
                ):
                    datos = obtener_trayectorias_satelitales(ahora=datetime.now(timezone.utc))

        self.assertEqual(datos['type'], 'FeatureCollection')
        self.assertEqual(datos['total_satelites_activos'], 1)
        self.assertEqual(datos['satelites_sobre_cuba'], 1)
        self.assertEqual(datos['fuente_tle'], 'CelesTrak visual (subset)')
        self.assertIn('parcial', datos['aviso'])
        self.assertEqual(
            {feature['properties']['tipo'] for feature in datos['features']},
            {'trayectoria', 'posicion', 'huella'},
        )
        huella = next(feature for feature in datos['features'] if feature['properties']['tipo'] == 'huella')
        self.assertEqual(huella['geometry']['type'], 'MultiPolygon')

    def test_error_orbital_sgp4_convierte_posicion_a_coordenadas(self):
        satelite = _parsear_tle(TLE_PRUEBA)[0][2]
        epoca = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(
            days=satelite.jdsatepoch + satelite.jdsatepochF - 2451545.0
        )

        posicion = _posicion_geografica(satelite, epoca)

        self.assertIsNotNone(posicion)
        longitud, latitud, altitud = posicion
        self.assertGreaterEqual(longitud, -180)
        self.assertLessEqual(longitud, 180)
        self.assertGreaterEqual(latitud, -90)
        self.assertLessEqual(latitud, 90)
        self.assertGreater(altitud, 0)
