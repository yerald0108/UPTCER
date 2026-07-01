import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.solicitudes.models import Solicitud, HistorialSolicitud
from apps.equipos.models import CategoriaEquipo, Equipo


# ─── Factory compartida ───────────────────────────────────────────────────────
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


def crear_solicitud(solicitante, flujo=Solicitud.FLUJO_F43, estado=Solicitud.ESTADO_ENVIADA):
    datos_f43 = {
        'nombre_apellidos':    solicitante.get_nombre_completo(),
        'numero_pasaporte':    'A12345678',
        'pais_residencia':     'Cuba',
        'direccion_residencia':'Calle 23 #456',
        'correo_electronico':  solicitante.email,
        'telefono':            '+53 5 123 4567',
        'provincia':           'la_habana',
        'modo_importacion':    'equipaje',
        'numero_vuelo':        'CU123',
        'fecha_arribo':        '2025-07-15',
        'pais_procedencia':    'Mexico',
        'aduana_acceso':       'Aeropuerto',
        'lugar_acceso':        'Aeropuerto Jose Marti',
        'numero_rad':          '',
        'objetivo_importacion':'empleo_directo',
        'objetivo_otros_detalle': '',
        'periodo_importacion': 'definitiva',
        'tiempo_solicitado':   '',
        'firma_ci':            '12345678901',
        'fecha_solicitud':     '2025-06-20',
        'equipos': [
            {
                'descripcion': 'Telefono inteligente',
                'marca':       'Samsung',
                'modelo':      'Galaxy S24',
                'cantidad':    1,
                'equipoId':    '',
                'listado':     False,
            }
        ],
    }
    return Solicitud.objects.create(
        flujo                = flujo,
        estado               = estado,
        solicitante          = solicitante,
        equipo_descripcion   = json.dumps(datos_f43, ensure_ascii=False),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — Solicitud
# ═══════════════════════════════════════════════════════════════════════════════

class SolicitudModelTest(TestCase):

    def setUp(self):
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')

    def test_numero_generado_automaticamente_f43(self):
        """El número F43 se genera automáticamente con el formato correcto."""
        solicitud = crear_solicitud(self.persona, flujo=Solicitud.FLUJO_F43)
        año = timezone.now().year
        self.assertTrue(solicitud.numero.startswith(f'F43-{año}-'))

    def test_numero_generado_automaticamente_rats(self):
        """El número RATS se genera automáticamente con el formato correcto."""
        solicitud = crear_solicitud(self.persona, flujo=Solicitud.FLUJO_RATS)
        año = timezone.now().year
        self.assertTrue(solicitud.numero.startswith(f'RAT-{año}-'))

    def test_numeros_son_unicos(self):
        """Dos solicitudes no pueden tener el mismo número."""
        s1 = crear_solicitud(self.persona)
        s2 = crear_solicitud(self.persona)
        self.assertNotEqual(s1.numero, s2.numero)

    def test_estado_por_defecto_es_borrador(self):
        """El estado por defecto de una solicitud es borrador."""
        solicitud = Solicitud.objects.create(
            flujo       = Solicitud.FLUJO_F43,
            solicitante = self.persona,
        )
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_BORRADOR)

    def test_propiedad_esta_pendiente(self):
        """esta_pendiente es True para estados enviada y en_revision."""
        s_enviada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)
        s_revision = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)
        s_aprobada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_APROBADA)

        self.assertTrue(s_enviada.esta_pendiente)
        self.assertTrue(s_revision.esta_pendiente)
        self.assertFalse(s_aprobada.esta_pendiente)

    def test_propiedad_esta_resuelta(self):
        """esta_resuelta es True para estados aprobada y denegada."""
        s_aprobada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_APROBADA)
        s_denegada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_DENEGADA)
        s_enviada  = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)

        self.assertTrue(s_aprobada.esta_resuelta)
        self.assertTrue(s_denegada.esta_resuelta)
        self.assertFalse(s_enviada.esta_resuelta)

    def test_propiedad_es_aprobada(self):
        """es_aprobada es True solo para estado aprobada."""
        s_aprobada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_APROBADA)
        s_denegada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_DENEGADA)

        self.assertTrue(s_aprobada.es_aprobada)
        self.assertFalse(s_denegada.es_aprobada)

    def test_clase_badge_por_estado(self):
        """clase_badge retorna la clase CSS correcta por estado."""
        casos = [
            (Solicitud.ESTADO_BORRADOR,    'badge-info'),
            (Solicitud.ESTADO_ENVIADA,     'badge-pendiente'),
            (Solicitud.ESTADO_EN_REVISION, 'badge-revision'),
            (Solicitud.ESTADO_APROBADA,    'badge-aprobado'),
            (Solicitud.ESTADO_DENEGADA,    'badge-denegado'),
        ]
        for estado, badge_esperado in casos:
            s = crear_solicitud(self.persona, estado=estado)
            self.assertEqual(s.clase_badge, badge_esperado,
                msg=f'Estado {estado} debería tener badge {badge_esperado}')

    def test_str_solicitud(self):
        """El __str__ incluye el número y el estado."""
        solicitud = crear_solicitud(self.persona)
        self.assertIn(solicitud.numero, str(solicitud))

    def test_relacion_solicitante(self):
        """La solicitud está relacionada correctamente con el solicitante."""
        solicitud = crear_solicitud(self.persona)
        self.assertEqual(solicitud.solicitante, self.persona)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — HistorialSolicitud
# ═══════════════════════════════════════════════════════════════════════════════

class HistorialSolicitudModelTest(TestCase):

    def setUp(self):
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.solicitud = crear_solicitud(self.persona)

    def test_crear_historial(self):
        """Se puede crear un registro de historial correctamente."""
        historial = HistorialSolicitud.objects.create(
            solicitud       = self.solicitud,
            estado_anterior = Solicitud.ESTADO_ENVIADA,
            estado_nuevo    = Solicitud.ESTADO_EN_REVISION,
            usuario         = self.operador,
            observacion     = 'En revisión por el operador.',
        )
        self.assertEqual(historial.solicitud, self.solicitud)
        self.assertEqual(historial.estado_anterior, Solicitud.ESTADO_ENVIADA)
        self.assertEqual(historial.estado_nuevo, Solicitud.ESTADO_EN_REVISION)
        self.assertEqual(historial.usuario, self.operador)

    def test_historial_relacionado_con_solicitud(self):
        """El historial se puede acceder desde la solicitud."""
        HistorialSolicitud.objects.create(
            solicitud       = self.solicitud,
            estado_anterior = Solicitud.ESTADO_ENVIADA,
            estado_nuevo    = Solicitud.ESTADO_EN_REVISION,
            usuario         = self.operador,
        )
        self.assertEqual(self.solicitud.historial.count(), 1)

    def test_get_estado_display_en_historial(self):
        """Los métodos get_estado_display funcionan en el historial."""
        historial = HistorialSolicitud.objects.create(
            solicitud       = self.solicitud,
            estado_anterior = Solicitud.ESTADO_ENVIADA,
            estado_nuevo    = Solicitud.ESTADO_APROBADA,
            usuario         = self.operador,
        )
        self.assertEqual(historial.get_estado_anterior_display(), 'Enviada')
        self.assertEqual(historial.get_estado_nuevo_display(), 'Aprobada')

    def test_clase_badge_historial(self):
        """clase_badge_nuevo retorna la clase CSS correcta."""
        historial = HistorialSolicitud.objects.create(
            solicitud       = self.solicitud,
            estado_anterior = Solicitud.ESTADO_ENVIADA,
            estado_nuevo    = Solicitud.ESTADO_APROBADA,
            usuario         = self.operador,
        )
        self.assertEqual(historial.clase_badge_nuevo, 'badge-aprobado')


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Solicitudes (control de acceso)
# ═══════════════════════════════════════════════════════════════════════════════

class SolicitudAccesoTest(TestCase):

    def setUp(self):
        self.client       = Client()
        self.persona      = crear_usuario(Usuario.ROL_PERSONA_NATURAL,  'persona')
        self.operador     = crear_usuario(Usuario.ROL_OPERADOR,         'operador')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA,     'especialista')
        self.solicitud    = crear_solicitud(self.persona)

    def test_nueva_f43_solo_persona_natural(self):
        """Solo persona natural puede acceder al formulario F43."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('solicitudes:nueva_f43'))
        self.assertEqual(response.status_code, 200)

    def test_nueva_f43_denegado_para_operador(self):
        """El operador no puede acceder al formulario F43."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('solicitudes:nueva_f43'))
        self.assertEqual(response.status_code, 302)

    def test_mis_solicitudes_solo_muestra_las_propias(self):
        """Mis solicitudes solo muestra las solicitudes del usuario autenticado."""
        otra_persona = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'otra')
        crear_solicitud(otra_persona)

        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('solicitudes:mis_solicitudes'))
        self.assertEqual(response.status_code, 200)

        solicitudes = response.context['solicitudes']
        for s in solicitudes:
            self.assertEqual(s.solicitante, self.persona)

    def test_lista_solicitudes_accesible_para_operador(self):
        """El operador puede ver la lista de todas las solicitudes."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('solicitudes:lista'))
        self.assertEqual(response.status_code, 200)

    def test_lista_solicitudes_denegada_para_persona_natural(self):
        """Persona natural no puede ver la lista general de solicitudes."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('solicitudes:lista'))
        self.assertEqual(response.status_code, 302)

    def test_detalle_solicitud_accesible_para_solicitante(self):
        """El solicitante puede ver el detalle de su propia solicitud."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(
            reverse('solicitudes:detalle', args=[self.solicitud.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detalle_solicitud_denegado_para_otra_persona(self):
        """Una persona natural no puede ver la solicitud de otra persona."""
        otra = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'otra')
        self.client.login(username='otra', password='test1234')
        response = self.client.get(
            reverse('solicitudes:detalle', args=[self.solicitud.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_detalle_solicitud_accesible_para_operador(self):
        """El operador puede ver el detalle de cualquier solicitud."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(
            reverse('solicitudes:detalle', args=[self.solicitud.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_sin_autenticar_redirige_login(self):
        """Sin autenticación redirige al login."""
        response = self.client.get(reverse('solicitudes:mis_solicitudes'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('acceso', response.url)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Cambio de estado
# ═══════════════════════════════════════════════════════════════════════════════

class CambioEstadoTest(TestCase):

    def setUp(self):
        self.client       = Client()
        self.persona      = crear_usuario(Usuario.ROL_PERSONA_NATURAL,  'persona')
        self.operador     = crear_usuario(Usuario.ROL_OPERADOR,         'operador')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA,     'especialista')
        self.solicitud    = crear_solicitud(self.persona)

    def test_operador_puede_cambiar_estado(self):
        """El operador puede cambiar el estado de una solicitud."""
        self.client.login(username='operador', password='test1234')
        response = self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_EN_REVISION,
                'observacion':  'Revisando la solicitud.',
            }
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, Solicitud.ESTADO_EN_REVISION)

    def test_persona_natural_no_puede_cambiar_estado(self):
        """La persona natural no puede cambiar el estado de su solicitud."""
        self.client.login(username='persona', password='test1234')
        response = self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {'estado_nuevo': Solicitud.ESTADO_APROBADA}
        )
        self.solicitud.refresh_from_db()
        self.assertNotEqual(self.solicitud.estado, Solicitud.ESTADO_APROBADA)

    def test_cambio_estado_registra_historial(self):
        """Cada cambio de estado crea un registro en el historial."""
        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_EN_REVISION,
                'observacion':  'Revisando.',
            }
        )
        self.assertEqual(self.solicitud.historial.count(), 1)
        historial = self.solicitud.historial.first()
        self.assertEqual(historial.estado_nuevo, Solicitud.ESTADO_EN_REVISION)
        self.assertEqual(historial.usuario, self.operador)

    def test_aprobar_solicitud_registra_fecha_resolucion(self):
        """Al aprobar se registra la fecha de resolución."""
        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_APROBADA,
                'observacion':  'Aprobada.',
            }
        )
        self.solicitud.refresh_from_db()
        self.assertIsNotNone(self.solicitud.fecha_resolucion)

    def test_aprobar_solicitud_genera_licencia(self):
        """Al aprobar una solicitud se genera automáticamente una licencia."""
        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_APROBADA,
                'observacion':  'Aprobada.',
            }
        )
        self.solicitud.refresh_from_db()
        self.assertTrue(hasattr(self.solicitud, 'licencia'))
        self.assertIsNotNone(self.solicitud.licencia)

    def test_estado_invalido_no_cambia_solicitud(self):
        """Un estado inválido no debe cambiar el estado de la solicitud."""
        estado_original = self.solicitud.estado
        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {'estado_nuevo': 'estado_inventado'}
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, estado_original)

    def test_cambio_estado_via_ajax_retorna_json(self):
        """El cambio de estado via AJAX retorna JSON."""
        self.client.login(username='operador', password='test1234')
        response = self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_EN_REVISION,
                'observacion':  'Revisando.',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['estado_nuevo'], Solicitud.ESTADO_EN_REVISION)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE FLUJO COMPLETO — F43
# ═══════════════════════════════════════════════════════════════════════════════

class FlujoF43CompletoTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')

    def test_flujo_completo_f43_aprobacion(self):
        """
        Flujo completo F43:
        1. Persona natural crea solicitud → ENVIADA
        2. Operador pone en revisión → EN_REVISION
        3. Operador aprueba → APROBADA + licencia generada
        """
        # Paso 1: Crear solicitud
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_ENVIADA)

        # Paso 2: Operador pone en revisión
        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_EN_REVISION,
                'observacion':  'Revisando documentación.',
            }
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_EN_REVISION)
        self.assertEqual(solicitud.historial.count(), 1)

        # Paso 3: Operador aprueba
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_APROBADA,
                'observacion':  'Documentación verificada. Aprobado.',
            }
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_APROBADA)
        self.assertEqual(solicitud.historial.count(), 2)
        self.assertTrue(hasattr(solicitud, 'licencia'))
        self.assertIsNotNone(solicitud.fecha_resolucion)

        # Verificar que el operador quedó asignado
        self.assertEqual(solicitud.operador_asignado, self.operador)

    def test_flujo_completo_f43_denegacion(self):
        """
        Flujo de denegación:
        1. Persona natural crea solicitud → ENVIADA
        2. Operador deniega → DENEGADA
        3. No se genera licencia
        """
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)

        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[solicitud.pk]),
            {
                'estado_nuevo': Solicitud.ESTADO_DENEGADA,
                'observacion':  'Documentación incompleta.',
            }
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_DENEGADA)
        self.assertFalse(hasattr(solicitud, 'licencia'))
        self.assertIsNotNone(solicitud.fecha_resolucion)

    def test_solicitud_resuelta_no_puede_cambiar_estado(self):
        """
        Una solicitud ya resuelta no debería poder cambiar de estado
        desde la vista — el formulario no aparece en el template.
        Verificamos que el estado no cambia si se intenta.
        """
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_APROBADA)
        solicitud.fecha_resolucion = timezone.now()
        solicitud.save()

        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[solicitud.pk]),
            {'estado_nuevo': Solicitud.ESTADO_DENEGADA}
        )
        solicitud.refresh_from_db()
        # El estado debe seguir siendo aprobada
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_APROBADA)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE FLUJO — Especialista
# ═══════════════════════════════════════════════════════════════════════════════

class FlujoEspecialistaTest(TestCase):

    def setUp(self):
        self.client       = Client()
        self.persona      = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador     = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA,    'especialista')

    def test_cola_evaluaciones_accesible_para_especialista(self):
        """El especialista puede acceder a la cola de evaluaciones."""
        self.client.login(username='especialista', password='test1234')
        response = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        self.assertEqual(response.status_code, 200)

    def test_cola_evaluaciones_denegada_para_persona_natural(self):
        """Persona natural no puede acceder a la cola de evaluaciones."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        self.assertEqual(response.status_code, 302)

    def test_cola_muestra_solo_equipos_no_listados_en_revision(self):
        """La cola solo muestra solicitudes con equipo no listado en revisión."""
        # Solicitud normal (listada)
        s_normal = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)

        # Solicitud con equipo no listado en revisión
        s_no_listada = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)
        s_no_listada.equipo_no_listado = True
        s_no_listada.save()

        self.client.login(username='especialista', password='test1234')
        response = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        pendientes = response.context['pendientes']

        self.assertIn(s_no_listada, pendientes)
        self.assertNotIn(s_normal, pendientes)

    def test_evaluar_solicitud_accesible_para_especialista(self):
        """El especialista puede acceder a la vista de evaluación."""
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)
        solicitud.equipo_no_listado = True
        solicitud.save()

        self.client.login(username='especialista', password='test1234')
        response = self.client.get(
            reverse('solicitudes:evaluar', args=[solicitud.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_evaluar_solicitud_denegado_para_operador(self):
        """El operador no puede acceder a la vista de evaluación del especialista."""
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)
        solicitud.equipo_no_listado = True
        solicitud.save()

        self.client.login(username='operador', password='test1234')
        response = self.client.get(
            reverse('solicitudes:evaluar', args=[solicitud.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_especialista_aprueba_solicitud(self):
        """El especialista puede aprobar una solicitud con equipo no listado."""
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)
        solicitud.equipo_no_listado    = True
        solicitud.equipo_marca_manual  = 'Samsung'
        solicitud.equipo_modelo_manual = 'Galaxy S24'
        solicitud.save()

        self.client.login(username='especialista', password='test1234')
        response = self.client.post(
            reverse('solicitudes:evaluar', args=[solicitud.pk]),
            {
                'banda_detectada':   'libre',
                'cumple_normativa':  '1',
                'criterio_tecnico':  'El equipo opera en banda libre 2.4 GHz. Cumple con la normativa.',
                'accion':            'aprobar',
                'agregar_catalogo':  '',
            }
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_APROBADA)
        self.assertIsNotNone(solicitud.fecha_resolucion)

    def test_especialista_deniega_solicitud(self):
        """El especialista puede denegar una solicitud con equipo no listado."""
        solicitud = crear_solicitud(self.persona, estado=Solicitud.ESTADO_EN_REVISION)
        solicitud.equipo_no_listado    = True
        solicitud.equipo_marca_manual  = 'Huawei'
        solicitud.equipo_modelo_manual = 'CPE Pro'
        solicitud.save()

        self.client.login(username='especialista', password='test1234')
        self.client.post(
            reverse('solicitudes:evaluar', args=[solicitud.pk]),
            {
                'banda_detectada':  'restringida',
                'cumple_normativa': '0',
                'criterio_tecnico': 'El equipo opera en frecuencia restringida. No cumple.',
                'accion':           'denegar',
                'agregar_catalogo': '',
            }
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, Solicitud.ESTADO_DENEGADA)