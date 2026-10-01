import json
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.solicitudes.models import Solicitud, HistorialSolicitud
from apps.equipos.models import Equipo, CategoriaEquipo


# ─── Factories ────────────────────────────────────────────────────────────────
def crear_usuario(rol, username=None, password='test1234'):
    username = username or f'user_{rol}'
    return Usuario.objects.create_user(
        username=username, email=f'{username}@uptcer.cu',
        nombre='Test', apellidos='Usuario', rol=rol, password=password,
    )


def crear_solicitud(solicitante, estado=Solicitud.ESTADO_ENVIADA,
                    categoria=Solicitud.CATEGORIA_MOVIL,
                    equipo_no_listado=False):
    datos = json.dumps({
        'nombre_apellidos': solicitante.get_nombre_completo(),
        'numero_pasaporte': 'A12345678',
        'pais_residencia': 'Cuba',
        'direccion_residencia': 'Calle 1 #1',
        'correo_electronico': solicitante.email,
        'telefono': '+53 5 000 0000',
        'provincia': 'la_habana',
        'modo_importacion': 'equipaje',
        'numero_vuelo': 'CU101',
        'fecha_arribo': '2026-01-01',
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
# Modelo Solicitud
# ═══════════════════════════════════════════════════════════════════════════════
class SolicitudModelTest(TestCase):

    def setUp(self):
        self.persona = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'sm_pn')

    def test_numero_generado_automaticamente_f43(self):
        """El número F43 se genera automáticamente con el formato correcto."""
        s = crear_solicitud(self.persona)
        self.assertRegex(s.numero, r'^F43-\d{4}-\d{4}$')

    def test_numero_generado_automaticamente_rats(self):
        """El número RATS se genera automáticamente con el formato correcto."""
        s = Solicitud(
            flujo=Solicitud.FLUJO_RATS, estado=Solicitud.ESTADO_ENVIADA,
            solicitante=self.persona, equipo_descripcion='{}',
        )
        s.save()
        self.assertRegex(s.numero, r'^RAT-\d{4}-\d{4}$')

    def test_numeros_son_unicos(self):
        """Dos solicitudes no pueden tener el mismo número."""
        s1 = crear_solicitud(self.persona)
        s2 = crear_solicitud(self.persona)
        self.assertNotEqual(s1.numero, s2.numero)

    def test_estado_por_defecto_es_borrador(self):
        """El estado por defecto de una solicitud es borrador."""
        s = Solicitud(
            flujo=Solicitud.FLUJO_F43, solicitante=self.persona,
            equipo_descripcion='{}',
        )
        s.save()
        self.assertEqual(s.estado, Solicitud.ESTADO_BORRADOR)

    def test_relacion_solicitante(self):
        """La solicitud está relacionada correctamente con el solicitante."""
        s = crear_solicitud(self.persona)
        self.assertEqual(s.solicitante, self.persona)

    def test_str_solicitud(self):
        """El __str__ incluye el número y el estado."""
        s = crear_solicitud(self.persona)
        texto = str(s)
        self.assertIn(s.numero, texto)

    def test_propiedad_esta_pendiente(self):
        """esta_pendiente es True para estados enviada, en_revision, en_revision_superior y pendiente_aprobacion."""
        for estado in [Solicitud.ESTADO_ENVIADA, Solicitud.ESTADO_EN_REVISION,
                       Solicitud.ESTADO_EN_REVISION_SUPERIOR,
                       Solicitud.ESTADO_PENDIENTE_APROBACION]:
            s = crear_solicitud(self.persona, estado=estado)
            self.assertTrue(s.esta_pendiente, f'Fallo para estado {estado}')

    def test_propiedad_esta_resuelta(self):
        """esta_resuelta es True para estados aprobada y denegada."""
        for estado in [Solicitud.ESTADO_APROBADA, Solicitud.ESTADO_DENEGADA]:
            s = crear_solicitud(self.persona, estado=estado)
            self.assertTrue(s.esta_resuelta, f'Fallo para estado {estado}')

    def test_propiedad_es_aprobada(self):
        """es_aprobada es True solo para estado aprobada."""
        s = crear_solicitud(self.persona, estado=Solicitud.ESTADO_APROBADA)
        self.assertTrue(s.es_aprobada)
        s2 = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)
        self.assertFalse(s2.es_aprobada)

    def test_clase_badge_por_estado(self):
        """clase_badge retorna la clase CSS correcta por estado."""
        casos = {
            Solicitud.ESTADO_ENVIADA:              'badge-pendiente',
            Solicitud.ESTADO_EN_REVISION:          'badge-revision',
            Solicitud.ESTADO_EN_REVISION_SUPERIOR: 'badge-revision',
            Solicitud.ESTADO_PENDIENTE_APROBACION: 'badge-pendiente',
            Solicitud.ESTADO_APROBADA:             'badge-aprobado',
            Solicitud.ESTADO_DENEGADA:             'badge-denegado',
        }
        for estado, badge in casos.items():
            s = crear_solicitud(self.persona, estado=estado)
            self.assertEqual(s.clase_badge, badge, f'Fallo para {estado}')

    def test_campo_categoria(self):
        """La categoría se guarda y recupera correctamente."""
        s = crear_solicitud(self.persona, categoria=Solicitud.CATEGORIA_MARITIMO)
        self.assertEqual(s.categoria, Solicitud.CATEGORIA_MARITIMO)


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo HistorialSolicitud
# ═══════════════════════════════════════════════════════════════════════════════
class HistorialSolicitudModelTest(TestCase):

    def setUp(self):
        self.persona = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'hs_pn')
        self.solicitud = crear_solicitud(self.persona)

    def test_crear_historial(self):
        """Se puede crear un registro de historial correctamente."""
        h = HistorialSolicitud.objects.create(
            solicitud=self.solicitud,
            estado_anterior=Solicitud.ESTADO_ENVIADA,
            estado_nuevo=Solicitud.ESTADO_EN_REVISION,
            usuario=self.persona,
            observacion='Test',
        )
        self.assertIsNotNone(h.pk)

    def test_historial_relacionado_con_solicitud(self):
        """El historial se puede acceder desde la solicitud."""
        HistorialSolicitud.objects.create(
            solicitud=self.solicitud,
            estado_anterior='',
            estado_nuevo=Solicitud.ESTADO_ENVIADA,
            usuario=self.persona,
            observacion='',
        )
        self.assertEqual(self.solicitud.historial.count(), 1)

    def test_get_estado_display_en_historial(self):
        """Los métodos get_estado_display funcionan en el historial."""
        h = HistorialSolicitud.objects.create(
            solicitud=self.solicitud,
            estado_anterior=Solicitud.ESTADO_ENVIADA,
            estado_nuevo=Solicitud.ESTADO_EN_REVISION,
            usuario=self.persona,
            observacion='',
        )
        self.assertIsNotNone(h.get_estado_nuevo_display())

    def test_clase_badge_historial(self):
        """clase_badge_nuevo retorna la clase CSS correcta."""
        h = HistorialSolicitud.objects.create(
            solicitud=self.solicitud,
            estado_anterior=Solicitud.ESTADO_ENVIADA,
            estado_nuevo=Solicitud.ESTADO_APROBADA,
            usuario=self.persona,
            observacion='',
        )
        self.assertEqual(h.clase_badge_nuevo, 'badge-aprobado')


# ═══════════════════════════════════════════════════════════════════════════════
# Control de acceso a vistas
# ═══════════════════════════════════════════════════════════════════════════════
class SolicitudAccesoTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.persona1 = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'ac_pn1')
        self.persona2 = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'ac_pn2')
        self.esp      = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'ac_esp')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'ac_dir')
        self.solicitud = crear_solicitud(self.persona1)

    def test_sin_autenticar_redirige_login(self):
        """Sin autenticación redirige al login."""
        r = self.client.get(reverse('solicitudes:mis_solicitudes'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_nueva_f43_solo_persona_natural(self):
        """Solo persona natural puede acceder al formulario F43."""
        self.client.login(username='ac_pn1', password='test1234')
        r = self.client.get(reverse('solicitudes:nueva_f43'))
        self.assertEqual(r.status_code, 200)

    def test_nueva_f43_denegado_para_especialista(self):
        """El especialista no puede acceder al formulario F43."""
        self.client.login(username='ac_esp', password='test1234')
        r = self.client.get(reverse('solicitudes:nueva_f43'))
        self.assertEqual(r.status_code, 302)

    def test_mis_solicitudes_solo_muestra_las_propias(self):
        """Mis solicitudes solo muestra las solicitudes del usuario autenticado."""
        crear_solicitud(self.persona2)
        self.client.login(username='ac_pn1', password='test1234')
        r = self.client.get(reverse('solicitudes:mis_solicitudes'))
        self.assertEqual(r.status_code, 200)
        for s in r.context['solicitudes']:
            self.assertEqual(s.solicitante, self.persona1)

    def test_detalle_solicitud_accesible_para_solicitante(self):
        """El solicitante puede ver el detalle de su propia solicitud."""
        self.client.login(username='ac_pn1', password='test1234')
        r = self.client.get(reverse('solicitudes:detalle', args=[self.solicitud.pk]))
        self.assertEqual(r.status_code, 200)

    def test_detalle_solicitud_denegado_para_otra_persona(self):
        """Una persona natural no puede ver la solicitud de otra persona."""
        self.client.login(username='ac_pn2', password='test1234')
        r = self.client.get(reverse('solicitudes:detalle', args=[self.solicitud.pk]))
        self.assertEqual(r.status_code, 302)

    def test_detalle_solicitud_accesible_para_especialista(self):
        """El especialista puede ver el detalle de cualquier solicitud."""
        self.client.login(username='ac_esp', password='test1234')
        r = self.client.get(reverse('solicitudes:detalle', args=[self.solicitud.pk]))
        self.assertEqual(r.status_code, 200)

    def test_lista_solicitudes_accesible_para_especialista(self):
        """El especialista puede ver la lista de solicitudes de su categoría."""
        self.client.login(username='ac_esp', password='test1234')
        r = self.client.get(reverse('solicitudes:lista'))
        self.assertEqual(r.status_code, 200)

    def test_lista_solicitudes_accesible_para_directivo(self):
        """El directivo puede ver la lista de todas las solicitudes."""
        self.client.login(username='ac_dir', password='test1234')
        r = self.client.get(reverse('solicitudes:lista'))
        self.assertEqual(r.status_code, 200)

    def test_lista_solicitudes_denegada_para_persona_natural(self):
        """Persona natural no puede ver la lista general de solicitudes."""
        self.client.login(username='ac_pn1', password='test1234')
        r = self.client.get(reverse('solicitudes:lista'))
        self.assertEqual(r.status_code, 302)


# ═══════════════════════════════════════════════════════════════════════════════
# Cambio de estado
# ═══════════════════════════════════════════════════════════════════════════════
class CambioEstadoTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'ce_pn')
        self.esp       = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'ce_esp')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'ce_dir')
        self.solicitud = crear_solicitud(self.persona)

    def _cambiar_estado(self, username, estado_nuevo, observacion='Test'):
        self.client.login(username=username, password='test1234')
        return self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {'estado_nuevo': estado_nuevo, 'observacion': observacion},
        )

    def test_especialista_puede_cambiar_estado(self):
        """El especialista puede cambiar el estado de una solicitud."""
        self._cambiar_estado('ce_esp', Solicitud.ESTADO_EN_REVISION)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, Solicitud.ESTADO_EN_REVISION)

    def test_persona_natural_no_puede_cambiar_estado(self):
        """La persona natural no puede cambiar el estado de su solicitud."""
        self._cambiar_estado('ce_pn', Solicitud.ESTADO_EN_REVISION)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, Solicitud.ESTADO_ENVIADA)

    def test_cambio_estado_registra_historial(self):
        """Cada cambio de estado crea un registro en el historial."""
        count_antes = HistorialSolicitud.objects.filter(
            solicitud=self.solicitud).count()
        self._cambiar_estado('ce_esp', Solicitud.ESTADO_EN_REVISION)
        count_despues = HistorialSolicitud.objects.filter(
            solicitud=self.solicitud).count()
        self.assertEqual(count_despues, count_antes + 1)

    def test_estado_invalido_no_cambia_solicitud(self):
        """Un estado inválido no debe cambiar el estado de la solicitud."""
        self._cambiar_estado('ce_esp', 'estado_que_no_existe')
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, Solicitud.ESTADO_ENVIADA)

    def test_aprobar_solicitud_genera_factura(self):
        """Al aprobar una solicitud se genera automáticamente una factura."""
        from apps.licencias.models import Factura
        self._cambiar_estado('ce_dir', Solicitud.ESTADO_APROBADA)
        self.solicitud.refresh_from_db()
        self.assertTrue(
            Factura.objects.filter(solicitud=self.solicitud).exists()
        )

    def test_aprobar_solicitud_registra_fecha_resolucion(self):
        """Al aprobar se registra la fecha de resolución."""
        self._cambiar_estado('ce_dir', Solicitud.ESTADO_APROBADA)
        self.solicitud.refresh_from_db()
        self.assertIsNotNone(self.solicitud.fecha_resolucion)

    def test_cambio_estado_via_ajax_retorna_json(self):
        """El cambio de estado via AJAX retorna JSON."""
        self.client.login(username='ce_esp', password='test1234')
        r = self.client.post(
            reverse('solicitudes:cambiar_estado', args=[self.solicitud.pk]),
            {'estado_nuevo': Solicitud.ESTADO_EN_REVISION, 'observacion': 'ok'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data.get('ok'))


# ═══════════════════════════════════════════════════════════════════════════════
# Flujo F43 completo
# ═══════════════════════════════════════════════════════════════════════════════
class FlujoF43CompletoTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'ff_pn')
        self.esp       = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'ff_esp')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'ff_dir')

    def _cambiar(self, username, solicitud, estado, obs='ok'):
        self.client.login(username=username, password='test1234')
        self.client.post(
            reverse('solicitudes:cambiar_estado', args=[solicitud.pk]),
            {'estado_nuevo': estado, 'observacion': obs},
        )
        solicitud.refresh_from_db()

    def test_flujo_completo_f43_aprobacion(self):
        """Flujo completo: enviada → en_revision → pendiente_aprobacion → aprobada → factura."""
        from apps.licencias.models import Factura
        s = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)

        self._cambiar('ff_esp', s, Solicitud.ESTADO_EN_REVISION)
        self.assertEqual(s.estado, Solicitud.ESTADO_EN_REVISION)

        self._cambiar('ff_esp', s, Solicitud.ESTADO_PENDIENTE_APROBACION)
        self.assertEqual(s.estado, Solicitud.ESTADO_PENDIENTE_APROBACION)

        self._cambiar('ff_dir', s, Solicitud.ESTADO_APROBADA)
        self.assertEqual(s.estado, Solicitud.ESTADO_APROBADA)

        self.assertTrue(Factura.objects.filter(solicitud=s).exists())

    def test_flujo_completo_f43_denegacion(self):
        """Flujo de denegación: enviada → en_revision → denegada."""
        s = crear_solicitud(self.persona, estado=Solicitud.ESTADO_ENVIADA)

        self._cambiar('ff_esp', s, Solicitud.ESTADO_EN_REVISION)
        self._cambiar('ff_esp', s, Solicitud.ESTADO_DENEGADA, obs='No cumple')

        self.assertEqual(s.estado, Solicitud.ESTADO_DENEGADA)
        self.assertTrue(s.esta_resuelta)

    def test_solicitud_resuelta_no_puede_cambiar_estado(self):
        """Una solicitud ya resuelta no puede cambiar de estado."""
        s = crear_solicitud(self.persona, estado=Solicitud.ESTADO_DENEGADA)
        self._cambiar('ff_dir', s, Solicitud.ESTADO_APROBADA)
        self.assertEqual(s.estado, Solicitud.ESTADO_DENEGADA)

    def test_flujo_equipo_no_listado_va_a_revision_superior(self):
        """Solicitud con equipo no listado inicia en en_revision_superior."""
        s = crear_solicitud(
            self.persona,
            estado=Solicitud.ESTADO_EN_REVISION_SUPERIOR,
            equipo_no_listado=True,
        )
        self.assertEqual(s.estado, Solicitud.ESTADO_EN_REVISION_SUPERIOR)
        self.assertTrue(s.equipo_no_listado)


# ═══════════════════════════════════════════════════════════════════════════════
# Flujo especialista superior
# ═══════════════════════════════════════════════════════════════════════════════
class FlujoEspecialistaSuperiorTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'es_pn')
        self.superior = crear_usuario(Usuario.ROL_ESPECIALISTA_SUPERIOR, 'es_sup')
        self.esp_base = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'es_esp')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'es_dir')
        self.solicitud = crear_solicitud(
            self.persona,
            estado=Solicitud.ESTADO_EN_REVISION_SUPERIOR,
            equipo_no_listado=True,
        )

    def test_cola_evaluaciones_accesible_para_superior(self):
        """El especialista superior puede acceder a la cola de evaluaciones."""
        self.client.login(username='es_sup', password='test1234')
        r = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        self.assertEqual(r.status_code, 200)

    def test_cola_evaluaciones_denegada_para_persona_natural(self):
        """Persona natural no puede acceder a la cola de evaluaciones."""
        self.client.login(username='es_pn', password='test1234')
        r = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        self.assertEqual(r.status_code, 302)

    def test_cola_evaluaciones_denegada_para_especialista_base(self):
        """El especialista de área no puede acceder a la cola del superior."""
        self.client.login(username='es_esp', password='test1234')
        r = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        self.assertEqual(r.status_code, 302)

    def test_cola_muestra_solicitudes_en_revision_superior(self):
        """La cola muestra solicitudes en estado en_revision_superior."""
        self.client.login(username='es_sup', password='test1234')
        r = self.client.get(reverse('solicitudes:cola_evaluaciones'))
        self.assertIn(self.solicitud, r.context['pendientes'].object_list)

    def test_evaluar_solicitud_accesible_para_superior(self):
        """El especialista superior puede acceder a la vista de evaluación."""
        self.client.login(username='es_sup', password='test1234')
        r = self.client.get(
            reverse('solicitudes:evaluar', args=[self.solicitud.pk])
        )
        self.assertEqual(r.status_code, 200)

    def test_evaluar_solicitud_denegado_para_especialista_base(self):
        """El especialista base no puede acceder a la vista de evaluación."""
        self.client.login(username='es_esp', password='test1234')
        r = self.client.get(
            reverse('solicitudes:evaluar', args=[self.solicitud.pk])
        )
        self.assertEqual(r.status_code, 302)

    def test_superior_aprueba_envia_a_pendiente_aprobacion(self):
        """El superior aprueba y la solicitud pasa a pendiente_aprobacion."""
        self.client.login(username='es_sup', password='test1234')
        self.client.post(
            reverse('solicitudes:evaluar', args=[self.solicitud.pk]),
            {
                'accion': 'aprobar',
                'criterio_tecnico': 'Equipo compatible con normativa',
                'banda_detectada': 'libre',
                'cumple_normativa': '1',
                'agregar_catalogo': '',
            }
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(
            self.solicitud.estado, Solicitud.ESTADO_PENDIENTE_APROBACION
        )

    def test_superior_deniega_cambia_estado_a_denegada(self):
        """El superior deniega y la solicitud pasa a denegada."""
        self.client.login(username='es_sup', password='test1234')
        self.client.post(
            reverse('solicitudes:evaluar', args=[self.solicitud.pk]),
            {
                'accion': 'denegar',
                'criterio_tecnico': 'No cumple normativa',
                'banda_detectada': 'restringida',
                'cumple_normativa': '',
                'agregar_catalogo': '',
            }
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, Solicitud.ESTADO_DENEGADA)