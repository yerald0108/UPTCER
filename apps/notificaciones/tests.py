import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.notificaciones.models import Notificacion
from apps.notificaciones.servicios import (
    notificar,
    notificar_operadores,
    notificar_especialistas,
    notificar_solicitud_nueva,
    notificar_derivacion_especialista,
    notificar_cambio_estado,
    notificar_criterio_tecnico,
)


# ─── Factories ────────────────────────────────────────────────────────────────
def crear_usuario(rol, username=None, password='test1234'):
    username = username or f'user_{rol}'
    return Usuario.objects.create_user(
        username  = username,
        email     = f'{username}@uptcer.cu',
        nombre    = 'Test',
        apellidos = 'Usuario',
        rol       = rol,
        password  = password,
    )


def crear_solicitud(solicitante):
    return Solicitud.objects.create(
        flujo       = Solicitud.FLUJO_F43,
        estado      = Solicitud.ESTADO_ENVIADA,
        solicitante = solicitante,
        equipo_descripcion = json.dumps({
            'equipos': [{'descripcion': 'Test', 'marca': 'Samsung', 'modelo': 'S24', 'cantidad': 1}]
        }),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — Notificacion
# ═══════════════════════════════════════════════════════════════════════════════

class NotificacionModelTest(TestCase):

    def setUp(self):
        self.operador = crear_usuario(Usuario.ROL_OPERADOR, 'operador')
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.solicitud = crear_solicitud(self.persona)

    def test_crear_notificacion(self):
        """Se puede crear una notificación correctamente."""
        n = Notificacion.objects.create(
            destinatario = self.operador,
            tipo         = Notificacion.TIPO_SOLICITUD_NUEVA,
            titulo       = 'Nueva solicitud',
            mensaje      = 'Hay una nueva solicitud.',
            solicitud    = self.solicitud,
        )
        self.assertEqual(n.destinatario, self.operador)
        self.assertFalse(n.leida)
        self.assertIsNone(n.fecha_lectura)

    def test_no_leida_por_defecto(self):
        """Una notificación nueva no está leída."""
        n = Notificacion.objects.create(
            destinatario = self.operador,
            tipo         = Notificacion.TIPO_GENERAL,
            titulo       = 'Test',
            mensaje      = 'Mensaje de prueba.',
        )
        self.assertFalse(n.leida)

    def test_marcar_leida(self):
        """marcar_leida actualiza el estado y registra la fecha."""
        n = Notificacion.objects.create(
            destinatario = self.operador,
            tipo         = Notificacion.TIPO_GENERAL,
            titulo       = 'Test',
            mensaje      = 'Mensaje.',
        )
        n.marcar_leida()
        self.assertTrue(n.leida)
        self.assertIsNotNone(n.fecha_lectura)

    def test_marcar_leida_idempotente(self):
        """Llamar marcar_leida dos veces no cambia la fecha de lectura."""
        n = Notificacion.objects.create(
            destinatario = self.operador,
            tipo         = Notificacion.TIPO_GENERAL,
            titulo       = 'Test',
            mensaje      = 'Mensaje.',
        )
        n.marcar_leida()
        fecha1 = n.fecha_lectura
        n.marcar_leida()
        self.assertEqual(n.fecha_lectura, fecha1)

    def test_clase_icono_por_tipo(self):
        """clase_icono retorna el icono correcto por tipo."""
        casos = [
            (Notificacion.TIPO_SOLICITUD_NUEVA,       'file-plus'),
            (Notificacion.TIPO_DERIVADA_ESPECIALISTA, 'alert-circle'),
            (Notificacion.TIPO_CAMBIO_ESTADO,         'refresh-cw'),
            (Notificacion.TIPO_CRITERIO_TECNICO,      'clipboard-check'),
            (Notificacion.TIPO_GENERAL,               'bell'),
        ]
        for tipo, icono_esperado in casos:
            n = Notificacion(tipo=tipo)
            self.assertEqual(n.clase_icono, icono_esperado,
                msg=f'Tipo {tipo} debería tener icono {icono_esperado}')

    def test_str_notificacion(self):
        """El __str__ incluye el título y el destinatario."""
        n = Notificacion.objects.create(
            destinatario = self.operador,
            tipo         = Notificacion.TIPO_GENERAL,
            titulo       = 'Título de prueba',
            mensaje      = 'Mensaje.',
        )
        self.assertIn('Título de prueba', str(n))
        self.assertIn('Test Usuario', str(n))


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE SERVICIOS — Notificaciones
# ═══════════════════════════════════════════════════════════════════════════════

class ServiciosNotificacionTest(TestCase):

    def setUp(self):
        self.persona      = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador1    = crear_usuario(Usuario.ROL_OPERADOR,        'operador1')
        self.operador2    = crear_usuario(Usuario.ROL_OPERADOR,        'operador2')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA,    'especialista')
        self.solicitud    = crear_solicitud(self.persona)

    def test_notificar_crea_notificacion(self):
        """notificar() crea una notificación para el destinatario."""
        notificar(
            destinatario = self.operador1,
            tipo         = Notificacion.TIPO_GENERAL,
            titulo       = 'Test',
            mensaje      = 'Mensaje de prueba.',
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.operador1).count(), 1
        )

    def test_notificar_operadores_notifica_a_todos(self):
        """notificar_operadores() notifica a todos los operadores activos."""
        notificar_operadores(
            tipo    = Notificacion.TIPO_SOLICITUD_NUEVA,
            titulo  = 'Nueva solicitud',
            mensaje = 'Hay una nueva solicitud.',
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.operador1).count(), 1
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.operador2).count(), 1
        )
        # El especialista no debe recibir esta notificación
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.especialista).count(), 0
        )

    def test_notificar_especialistas_notifica_a_todos(self):
        """notificar_especialistas() notifica a todos los especialistas activos."""
        notificar_especialistas(
            tipo    = Notificacion.TIPO_DERIVADA_ESPECIALISTA,
            titulo  = 'Equipo no listado',
            mensaje = 'Hay un equipo no listado para evaluar.',
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.especialista).count(), 1
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.operador1).count(), 0
        )

    def test_notificar_solicitud_nueva(self):
        """notificar_solicitud_nueva() notifica a todos los operadores."""
        notificar_solicitud_nueva(self.solicitud)
        self.assertEqual(
            Notificacion.objects.filter(
                tipo      = Notificacion.TIPO_SOLICITUD_NUEVA,
                solicitud = self.solicitud,
            ).count(), 2  # operador1 y operador2
        )

    def test_notificar_derivacion_especialista(self):
        """notificar_derivacion_especialista() notifica a los especialistas."""
        self.solicitud.equipo_no_listado    = True
        self.solicitud.equipo_marca_manual  = 'Samsung'
        self.solicitud.equipo_modelo_manual = 'Galaxy S24'
        self.solicitud.save()

        notificar_derivacion_especialista(self.solicitud)
        self.assertEqual(
            Notificacion.objects.filter(
                tipo      = Notificacion.TIPO_DERIVADA_ESPECIALISTA,
                solicitud = self.solicitud,
                destinatario = self.especialista,
            ).count(), 1
        )

    def test_notificar_cambio_estado(self):
        """notificar_cambio_estado() notifica al solicitante."""
        notificar_cambio_estado(
            solicitud         = self.solicitud,
            estado_anterior   = Solicitud.ESTADO_ENVIADA,
            usuario_responsable = self.operador1,
        )
        self.assertEqual(
            Notificacion.objects.filter(
                tipo         = Notificacion.TIPO_CAMBIO_ESTADO,
                destinatario = self.persona,
                solicitud    = self.solicitud,
            ).count(), 1
        )

    def test_notificar_criterio_tecnico(self):
        """notificar_criterio_tecnico() notifica a los operadores."""
        notificar_criterio_tecnico(self.solicitud)
        self.assertEqual(
            Notificacion.objects.filter(
                tipo      = Notificacion.TIPO_CRITERIO_TECNICO,
                solicitud = self.solicitud,
            ).count(), 2  # operador1 y operador2
        )

    def test_operador_inactivo_no_recibe_notificacion(self):
        """Un operador inactivo no recibe notificaciones."""
        self.operador2.is_active = False
        self.operador2.save()

        notificar_operadores(
            tipo    = Notificacion.TIPO_SOLICITUD_NUEVA,
            titulo  = 'Test',
            mensaje = 'Test.',
        )
        self.assertEqual(
            Notificacion.objects.filter(destinatario=self.operador2).count(), 0
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Notificaciones
# ═══════════════════════════════════════════════════════════════════════════════

class NotificacionVistaTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.solicitud = crear_solicitud(self.persona)

        self.notif = Notificacion.objects.create(
            destinatario = self.operador,
            tipo         = Notificacion.TIPO_SOLICITUD_NUEVA,
            titulo       = 'Nueva solicitud de prueba',
            mensaje      = 'Hay una nueva solicitud.',
            solicitud    = self.solicitud,
        )

    def test_lista_notificaciones_accesible(self):
        """La lista de notificaciones es accesible para cualquier usuario."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('notificaciones:lista'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notificaciones/lista.html')

    def test_lista_marca_notificaciones_como_leidas(self):
        """Al abrir la lista las notificaciones se marcan como leídas."""
        self.assertFalse(self.notif.leida)
        self.client.login(username='operador', password='test1234')
        self.client.get(reverse('notificaciones:lista'))
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.leida)

    def test_lista_sin_autenticar_redirige(self):
        """Sin autenticación redirige al login."""
        response = self.client.get(reverse('notificaciones:lista'))
        self.assertEqual(response.status_code, 302)

    def test_contador_retorna_json(self):
        """El endpoint contador retorna JSON con el conteo correcto."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('notificaciones:contador'))
        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 1)

    def test_contador_cero_sin_notificaciones(self):
        """El contador retorna 0 cuando no hay notificaciones no leídas."""
        self.notif.marcar_leida()
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('notificaciones:contador'))
        import json
        data = json.loads(response.content)
        self.assertEqual(data['count'], 0)

    def test_marcar_leida_redirige_a_solicitud(self):
        """Marcar una notificación como leída redirige a la solicitud."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(
            reverse('notificaciones:marcar_leida', args=[self.notif.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.leida)

    def test_usuario_no_puede_ver_notificaciones_de_otro(self):
        """Un usuario no puede marcar como leída la notificación de otro."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(
            reverse('notificaciones:marcar_leida', args=[self.notif.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_lista_solo_muestra_notificaciones_propias(self):
        """La lista solo muestra las notificaciones del usuario autenticado."""
        notif_persona = Notificacion.objects.create(
            destinatario = self.persona,
            tipo         = Notificacion.TIPO_GENERAL,
            titulo       = 'Para persona',
            mensaje      = 'Solo para persona.',
        )
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('notificaciones:lista'))
        notificaciones = list(response.context['notificaciones'])

        titulos = [n.titulo for n in notificaciones]
        self.assertIn('Nueva solicitud de prueba', titulos)
        self.assertNotIn('Para persona', titulos)