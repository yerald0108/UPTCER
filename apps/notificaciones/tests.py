import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.notificaciones.models import Notificacion
from apps.notificaciones.servicios import (
    notificar,
    notificar_solicitud_nueva,
    notificar_cambio_estado,
    notificar_derivacion_superior,
    notificar_pendiente_aprobacion,
    notificar_criterio_tecnico,
    notificar_especialistas_por_categoria,
    notificar_especialistas_superiores,
    notificar_directivos,
)


def crear_usuario(rol, username=None, password='test1234'):
    username = username or f'user_{rol}'
    return Usuario.objects.create_user(
        username=username, email=f'{username}@uptcer.cu',
        nombre='Test', apellidos='Usuario', rol=rol, password=password,
    )


def crear_solicitud(solicitante, categoria=Solicitud.CATEGORIA_MOVIL,
                    estado=Solicitud.ESTADO_ENVIADA,
                    equipo_no_listado=False):
    datos = json.dumps({
        'nombre_apellidos': solicitante.get_nombre_completo(),
        'numero_pasaporte': 'A12345678',
        'pais_residencia': 'Cuba',
        'direccion_residencia': 'Calle 1',
        'correo_electronico': solicitante.email,
        'telefono': '+53 5 000 0000',
        'provincia': 'la_habana',
        'modo_importacion': 'equipaje',
        'numero_vuelo': '', 'fecha_arribo': '',
        'pais_procedencia': 'Mexico',
        'aduana_acceso': 'Aeropuerto',
        'lugar_acceso': 'Aeropuerto Jose Marti',
        'numero_rad': '',
        'objetivo_importacion': 'empleo_directo',
        'objetivo_otros_detalle': '',
        'periodo_importacion': 'definitiva',
        'tiempo_solicitado': '',
        'firma_ci': '90123456789',
        'fecha_solicitud': timezone.now().date().isoformat(),
        'equipos': [{'descripcion': 'Telefono', 'marca': 'Samsung',
                     'modelo': 'Galaxy S24', 'cantidad': 1,
                     'equipoId': '', 'listado': False}],
    }, ensure_ascii=False)

    s = Solicitud(
        flujo=Solicitud.FLUJO_F43,
        categoria=categoria,
        estado=estado,
        solicitante=solicitante,
        equipo_descripcion=datos,
        equipo_no_listado=equipo_no_listado,
        equipo_marca_manual='DJI' if equipo_no_listado else '',
        equipo_modelo_manual='Mini 4' if equipo_no_listado else '',
    )
    s.save()
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo Notificacion
# ═══════════════════════════════════════════════════════════════════════════════
class NotificacionModelTest(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'nm_pn')

    def test_crear_notificacion(self):
        """Se puede crear una notificación correctamente."""
        n = Notificacion.objects.create(
            destinatario=self.usuario,
            tipo=Notificacion.TIPO_GENERAL,
            titulo='Test',
            mensaje='Mensaje de prueba',
        )
        self.assertIsNotNone(n.pk)
        self.assertFalse(n.leida)

    def test_marcar_leida(self):
        """marcar_leida cambia el estado y registra la fecha."""
        n = Notificacion.objects.create(
            destinatario=self.usuario,
            tipo=Notificacion.TIPO_GENERAL,
            titulo='Test',
            mensaje='Test',
        )
        n.marcar_leida()
        self.assertTrue(n.leida)
        self.assertIsNotNone(n.fecha_lectura)

    def test_clase_icono_por_tipo(self):
        """clase_icono retorna el icono correcto según el tipo."""
        tipos_iconos = {
            Notificacion.TIPO_SOLICITUD_NUEVA:       'file-plus',
            Notificacion.TIPO_CAMBIO_ESTADO:         'refresh-cw',
            Notificacion.TIPO_DERIVADA_ESPECIALISTA: 'alert-circle',
            Notificacion.TIPO_CRITERIO_TECNICO:      'clipboard-check',
            Notificacion.TIPO_GENERAL:               'bell',
        }
        for tipo, icono in tipos_iconos.items():
            n = Notificacion(tipo=tipo)
            self.assertEqual(n.clase_icono, icono, f'Fallo para tipo {tipo}')

    def test_str_notificacion(self):
        """El __str__ incluye el título."""
        n = Notificacion.objects.create(
            destinatario=self.usuario,
            tipo=Notificacion.TIPO_GENERAL,
            titulo='Mi notificación',
            mensaje='Test',
        )
        self.assertIn('Mi notificación', str(n))


# ═══════════════════════════════════════════════════════════════════════════════
# Servicios de notificación
# ═══════════════════════════════════════════════════════════════════════════════
class ServiciosNotificacionTest(TestCase):

    def setUp(self):
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'sn_pn')
        self.esp_movil = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'sn_esp_m')
        self.esp_radio = crear_usuario(Usuario.ROL_ESPECIALISTA_RADIOFARO, 'sn_esp_r')
        self.superior  = crear_usuario(Usuario.ROL_ESPECIALISTA_SUPERIOR, 'sn_sup')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'sn_dir')
        self.solicitud_movil = crear_solicitud(
            self.persona, categoria=Solicitud.CATEGORIA_MOVIL
        )
        self.solicitud_no_listado = crear_solicitud(
            self.persona,
            estado=Solicitud.ESTADO_EN_REVISION_SUPERIOR,
            equipo_no_listado=True,
        )

    def test_notificar_solicitud_nueva_notifica_especialista_movil(self):
        """notificar_solicitud_nueva notifica al especialista de la categoría."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.esp_movil).count()
        notificar_solicitud_nueva(self.solicitud_movil)
        count_despues = Notificacion.objects.filter(
            destinatario=self.esp_movil).count()
        self.assertGreater(count_despues, count_antes)

    def test_notificar_solicitud_nueva_no_notifica_especialista_incorrecto(self):
        """notificar_solicitud_nueva no notifica a especialistas de otras áreas."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.esp_radio).count()
        notificar_solicitud_nueva(self.solicitud_movil)
        count_despues = Notificacion.objects.filter(
            destinatario=self.esp_radio).count()
        self.assertEqual(count_despues, count_antes)

    def test_notificar_derivacion_superior_notifica_al_superior(self):
        """notificar_derivacion_superior notifica al especialista superior."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.superior).count()
        notificar_derivacion_superior(self.solicitud_no_listado)
        count_despues = Notificacion.objects.filter(
            destinatario=self.superior).count()
        self.assertGreater(count_despues, count_antes)

    def test_notificar_pendiente_aprobacion_notifica_directivo(self):
        """notificar_pendiente_aprobacion notifica al directivo."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.directivo).count()
        notificar_pendiente_aprobacion(self.solicitud_movil)
        count_despues = Notificacion.objects.filter(
            destinatario=self.directivo).count()
        self.assertGreater(count_despues, count_antes)

    def test_notificar_cambio_estado_notifica_al_solicitante(self):
        """notificar_cambio_estado notifica al solicitante."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.persona).count()
        notificar_cambio_estado(
            self.solicitud_movil,
            Solicitud.ESTADO_ENVIADA,
            self.esp_movil,
        )
        count_despues = Notificacion.objects.filter(
            destinatario=self.persona).count()
        self.assertGreater(count_despues, count_antes)

    def test_notificar_especialistas_por_categoria_correcto(self):
        """notificar_especialistas_por_categoria notifica solo a la categoría correcta."""
        count_movil_antes = Notificacion.objects.filter(
            destinatario=self.esp_movil).count()
        count_radio_antes = Notificacion.objects.filter(
            destinatario=self.esp_radio).count()

        notificar_especialistas_por_categoria(
            'movil',
            Notificacion.TIPO_GENERAL,
            'Test',
            'Mensaje test',
        )
        self.assertGreater(
            Notificacion.objects.filter(destinatario=self.esp_movil).count(),
            count_movil_antes
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.esp_radio).count(),
            count_radio_antes
        )

    def test_notificar_especialistas_superiores(self):
        """notificar_especialistas_superiores notifica al superior."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.superior).count()
        notificar_especialistas_superiores(
            Notificacion.TIPO_GENERAL, 'Test', 'Mensaje'
        )
        self.assertGreater(
            Notificacion.objects.filter(destinatario=self.superior).count(),
            count_antes
        )

    def test_notificar_directivos(self):
        """notificar_directivos notifica al directivo."""
        count_antes = Notificacion.objects.filter(
            destinatario=self.directivo).count()
        notificar_directivos(
            Notificacion.TIPO_GENERAL, 'Test', 'Mensaje'
        )
        self.assertGreater(
            Notificacion.objects.filter(destinatario=self.directivo).count(),
            count_antes
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Vistas de notificaciones
# ═══════════════════════════════════════════════════════════════════════════════
class NotificacionVistaTest(TestCase):

    def setUp(self):
        self.client  = Client()
        self.usuario = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'nv_pn')
        self.notif   = Notificacion.objects.create(
            destinatario=self.usuario,
            tipo=Notificacion.TIPO_GENERAL,
            titulo='Notif test',
            mensaje='Mensaje test',
        )

    def test_lista_notificaciones_accesible(self):
        """El usuario puede ver su lista de notificaciones."""
        self.client.login(username='nv_pn', password='test1234')
        r = self.client.get(reverse('notificaciones:lista'))
        self.assertEqual(r.status_code, 200)

    def test_lista_sin_autenticar_redirige(self):
        """Sin autenticación redirige al login."""
        r = self.client.get(reverse('notificaciones:lista'))
        self.assertEqual(r.status_code, 302)

    def test_contador_ajax_retorna_json(self):
        """El contador AJAX retorna JSON con el conteo de no leídas."""
        self.client.login(username='nv_pn', password='test1234')
        r = self.client.get(
            reverse('notificaciones:contador'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 1)

    def test_contador_decrece_al_marcar_leida(self):
        """El contador decrece al marcar una notificación como leída."""
        self.notif.marcar_leida()
        self.client.login(username='nv_pn', password='test1234')
        r = self.client.get(
            reverse('notificaciones:contador'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        data = json.loads(r.content)
        self.assertEqual(data['count'], 0)

    def test_usuario_solo_ve_sus_notificaciones(self):
        """Un usuario solo ve sus propias notificaciones."""
        otro = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'nv_pn2')
        Notificacion.objects.create(
            destinatario=otro,
            tipo=Notificacion.TIPO_GENERAL,
            titulo='Notif otro',
            mensaje='No debería verse',
        )
        self.client.login(username='nv_pn', password='test1234')
        r = self.client.get(reverse('notificaciones:lista'))
        for n in r.context['notificaciones']:
            self.assertEqual(n.destinatario, self.usuario)