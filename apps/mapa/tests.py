from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import Usuario
from apps.licencias.models import Licencia
from apps.mapa.models import PuntoMapa
from apps.solicitudes.models import Solicitud


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
            atributos={'equipos': [{'descripcion': 'Teléfono'}]},
        )

        response = self.client.get(reverse('mapa:api_puntos'))
        properties = response.json()['features'][0]['properties']

        self.assertEqual(properties['licencia_numero'], licencia.numero)
        self.assertEqual(properties['solicitante'], 'Ana Solicitante')
        self.assertEqual(properties['direccion_instalacion'], 'Calle 1, La Habana')
