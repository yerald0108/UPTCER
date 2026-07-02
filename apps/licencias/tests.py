import json
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.licencias.models import Licencia
from apps.licencias.servicios import generar_licencia


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


def crear_solicitud_aprobada(solicitante, operador, periodo='definitiva', meses=None):
    datos_f43 = {
        'nombre_apellidos':    solicitante.get_nombre_completo(),
        'numero_pasaporte':    'A12345678',
        'pais_residencia':     'Cuba',
        'direccion_residencia':'Calle 23 #456',
        'correo_electronico':  solicitante.email,
        'telefono':            '+53 5 123 4567',
        'provincia':           'la_habana',
        'modo_importacion':    'equipaje',
        'numero_vuelo':        '',
        'fecha_arribo':        '',
        'pais_procedencia':    '',
        'aduana_acceso':       '',
        'lugar_acceso':        '',
        'numero_rad':          '',
        'objetivo_importacion':'empleo_directo',
        'objetivo_otros_detalle': '',
        'periodo_importacion': periodo,
        'tiempo_solicitado':   str(meses) if meses else '',
        'firma_ci':            '12345678901',
        'fecha_solicitud':     '2025-06-20',
        'equipos': [
            {
                'descripcion': 'Telefono inteligente',
                'marca':       'Samsung',
                'modelo':      'Galaxy S24',
                'cantidad':    1,
            }
        ],
    }
    solicitud = Solicitud.objects.create(
        flujo              = Solicitud.FLUJO_F43,
        estado             = Solicitud.ESTADO_APROBADA,
        solicitante        = solicitante,
        operador_asignado  = operador,
        fecha_resolucion   = timezone.now(),
        equipo_descripcion = json.dumps(datos_f43, ensure_ascii=False),
    )
    return solicitud


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — Licencia
# ═══════════════════════════════════════════════════════════════════════════════

class LicenciaModelTest(TestCase):

    def setUp(self):
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.solicitud = crear_solicitud_aprobada(self.persona, self.operador)

    def test_numero_generado_automaticamente(self):
        """El número de licencia se genera automáticamente con formato correcto."""
        licencia = generar_licencia(self.solicitud, self.operador)
        año = timezone.now().year
        self.assertTrue(licencia.numero.startswith(f'LIC-{año}-'))

    def test_numeros_unicos(self):
        """Dos licencias no pueden tener el mismo número."""
        s2 = crear_solicitud_aprobada(self.persona, self.operador)
        l1 = generar_licencia(self.solicitud, self.operador)
        l2 = generar_licencia(s2, self.operador)
        self.assertNotEqual(l1.numero, l2.numero)

    def test_estado_vigente_por_defecto(self):
        """Una licencia nueva está vigente por defecto."""
        licencia = generar_licencia(self.solicitud, self.operador)
        self.assertEqual(licencia.estado, Licencia.ESTADO_VIGENTE)

    def test_licencia_definitiva_sin_vencimiento(self):
        """Una licencia definitiva no tiene fecha de vencimiento."""
        licencia = generar_licencia(self.solicitud, self.operador)
        self.assertIsNone(licencia.fecha_vencimiento)
        self.assertFalse(licencia.es_temporal)

    def test_licencia_temporal_con_vencimiento(self):
        """Una licencia temporal tiene fecha de vencimiento calculada."""
        solicitud_temporal = crear_solicitud_aprobada(
            self.persona, self.operador,
            periodo='temporal', meses=6
        )
        licencia = generar_licencia(solicitud_temporal, self.operador)
        self.assertIsNotNone(licencia.fecha_vencimiento)
        self.assertTrue(licencia.es_temporal)
        # La fecha de vencimiento debe ser en el futuro
        self.assertGreater(licencia.fecha_vencimiento, date.today())

    def test_licencia_temporal_6_meses(self):
        """La fecha de vencimiento de 6 meses es correcta."""
        from dateutil.relativedelta import relativedelta
        solicitud_temporal = crear_solicitud_aprobada(
            self.persona, self.operador,
            periodo='temporal', meses=6
        )
        licencia = generar_licencia(solicitud_temporal, self.operador)
        esperado = date.today() + relativedelta(months=6)
        self.assertEqual(licencia.fecha_vencimiento, esperado)

    def test_es_vigente_sin_vencimiento(self):
        """Una licencia definitiva vigente es_vigente = True."""
        licencia = generar_licencia(self.solicitud, self.operador)
        self.assertTrue(licencia.es_vigente)

    def test_es_vigente_temporal_no_vencida(self):
        """Una licencia temporal no vencida es_vigente = True."""
        solicitud_temporal = crear_solicitud_aprobada(
            self.persona, self.operador,
            periodo='temporal', meses=6
        )
        licencia = generar_licencia(solicitud_temporal, self.operador)
        self.assertTrue(licencia.es_vigente)

    def test_verificar_vencimiento_actualiza_estado(self):
        """verificar_vencimiento actualiza el estado si la fecha venció."""
        solicitud_temporal = crear_solicitud_aprobada(
            self.persona, self.operador,
            periodo='temporal', meses=1
        )
        licencia = generar_licencia(solicitud_temporal, self.operador)
        # Forzar fecha de vencimiento al pasado
        licencia.fecha_vencimiento = date(2020, 1, 1)
        licencia.save()
        licencia.verificar_vencimiento()
        self.assertEqual(licencia.estado, Licencia.ESTADO_VENCIDA)

    def test_generar_licencia_no_duplica(self):
        """Llamar generar_licencia dos veces no crea dos licencias."""
        l1 = generar_licencia(self.solicitud, self.operador)
        l2 = generar_licencia(self.solicitud, self.operador)
        self.assertEqual(l1.pk, l2.pk)
        self.assertEqual(Licencia.objects.filter(solicitud=self.solicitud).count(), 1)

    def test_str_licencia(self):
        """El __str__ incluye el número y el estado."""
        licencia = generar_licencia(self.solicitud, self.operador)
        self.assertIn(licencia.numero, str(licencia))
        self.assertIn('Vigente', str(licencia))

    def test_clase_badge_vigente(self):
        """clase_badge retorna badge-aprobado para licencia vigente."""
        licencia = generar_licencia(self.solicitud, self.operador)
        self.assertEqual(licencia.clase_badge, 'badge-aprobado')

    def test_clase_badge_revocada(self):
        """clase_badge retorna badge-denegado para licencia revocada."""
        licencia = generar_licencia(self.solicitud, self.operador)
        licencia.estado = Licencia.ESTADO_REVOCADA
        licencia.save()
        self.assertEqual(licencia.clase_badge, 'badge-denegado')

    def test_relacion_con_solicitud(self):
        """La licencia está relacionada correctamente con la solicitud."""
        licencia = generar_licencia(self.solicitud, self.operador)
        self.assertEqual(licencia.solicitud, self.solicitud)
        self.assertEqual(self.solicitud.licencia, licencia)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Licencias
# ═══════════════════════════════════════════════════════════════════════════════

class LicenciaVistaTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO,      'directivo')
        self.otra_persona = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'otra')
        self.solicitud = crear_solicitud_aprobada(self.persona, self.operador)
        self.licencia  = generar_licencia(self.solicitud, self.operador)

    def test_lista_licencias_accesible_para_persona(self):
        """Persona natural puede ver su lista de licencias."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('licencias:lista'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licencias/lista.html')

    def test_lista_licencias_persona_solo_ve_las_suyas(self):
        """Persona natural solo ve sus propias licencias."""
        solicitud_otra = crear_solicitud_aprobada(self.otra_persona, self.operador)
        licencia_otra  = generar_licencia(solicitud_otra, self.operador)

        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('licencias:lista'))
        licencias = list(response.context['licencias'])

        self.assertIn(self.licencia, licencias)
        self.assertNotIn(licencia_otra, licencias)

    def test_lista_licencias_operador_ve_todas(self):
        """El operador ve todas las licencias."""
        solicitud_otra = crear_solicitud_aprobada(self.otra_persona, self.operador)
        licencia_otra  = generar_licencia(solicitud_otra, self.operador)

        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('licencias:lista'))
        licencias = list(response.context['licencias'])

        self.assertIn(self.licencia, licencias)
        self.assertIn(licencia_otra, licencias)

    def test_detalle_licencia_accesible_para_solicitante(self):
        """El solicitante puede ver el detalle de su licencia."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(
            reverse('licencias:detalle', args=[self.licencia.numero])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'licencias/detalle.html')

    def test_detalle_licencia_denegado_para_otra_persona(self):
        """Otra persona no puede ver la licencia de alguien más."""
        self.client.login(username='otra', password='test1234')
        response = self.client.get(
            reverse('licencias:detalle', args=[self.licencia.numero])
        )
        self.assertEqual(response.status_code, 302)

    def test_detalle_licencia_accesible_para_operador(self):
        """El operador puede ver cualquier licencia."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(
            reverse('licencias:detalle', args=[self.licencia.numero])
        )
        self.assertEqual(response.status_code, 200)

    def test_revocar_licencia_solo_operador(self):
        """Solo el operador puede revocar una licencia."""
        self.client.login(username='operador', password='test1234')
        response = self.client.post(
            reverse('licencias:revocar', args=[self.licencia.numero]),
            {'motivo': 'Documentación fraudulenta detectada.'}
        )
        self.licencia.refresh_from_db()
        self.assertEqual(self.licencia.estado, Licencia.ESTADO_REVOCADA)
        self.assertEqual(self.licencia.motivo_revocacion, 'Documentación fraudulenta detectada.')
        self.assertIsNotNone(self.licencia.fecha_revocacion)

    def test_revocar_licencia_denegado_para_persona_natural(self):
        """Persona natural no puede revocar licencias."""
        self.client.login(username='persona', password='test1234')
        response = self.client.post(
            reverse('licencias:revocar', args=[self.licencia.numero]),
            {'motivo': 'Intento no autorizado.'}
        )
        self.licencia.refresh_from_db()
        self.assertEqual(self.licencia.estado, Licencia.ESTADO_VIGENTE)

    def test_revocar_sin_motivo_no_revoca(self):
        """Revocar sin especificar motivo no cambia el estado."""
        self.client.login(username='operador', password='test1234')
        self.client.post(
            reverse('licencias:revocar', args=[self.licencia.numero]),
            {'motivo': ''}
        )
        self.licencia.refresh_from_db()
        self.assertEqual(self.licencia.estado, Licencia.ESTADO_VIGENTE)

    def test_lista_sin_autenticar_redirige(self):
        """Sin autenticación redirige al login."""
        response = self.client.get(reverse('licencias:lista'))
        self.assertEqual(response.status_code, 302)

    def test_filtro_por_estado_vigente(self):
        """El filtro por estado funciona correctamente."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(
            reverse('licencias:lista'),
            {'estado': Licencia.ESTADO_VIGENTE}
        )
        licencias = list(response.context['licencias'])
        for l in licencias:
            self.assertEqual(l.estado, Licencia.ESTADO_VIGENTE)