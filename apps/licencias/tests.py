import json
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.licencias.models import Licencia, Factura
from apps.licencias.servicios import generar_licencia, generar_factura, registrar_pago


def crear_usuario(rol, username=None, password='test1234'):
    username = username or f'user_{rol}'
    return Usuario.objects.create_user(
        username=username, email=f'{username}@uptcer.cu',
        nombre='Test', apellidos='Usuario', rol=rol, password=password,
    )


def crear_solicitud(solicitante, periodo='definitiva', meses=''):
    datos = json.dumps({
        'nombre_apellidos': solicitante.get_nombre_completo(),
        'numero_pasaporte': 'A12345678',
        'pais_residencia': 'Cuba',
        'direccion_residencia': 'Calle 1',
        'correo_electronico': solicitante.email,
        'telefono': '+53 5 000 0000',
        'provincia': 'la_habana',
        'modo_importacion': 'equipaje',
        'numero_vuelo': '',
        'fecha_arribo': '',
        'pais_procedencia': 'Mexico',
        'aduana_acceso': 'Aeropuerto',
        'lugar_acceso': 'Aeropuerto Jose Marti',
        'numero_rad': '',
        'objetivo_importacion': 'empleo_directo',
        'objetivo_otros_detalle': '',
        'periodo_importacion': periodo,
        'tiempo_solicitado': meses,
        'firma_ci': '90123456789',
        'fecha_solicitud': timezone.now().date().isoformat(),
        'equipos': [{'descripcion': 'Telefono', 'marca': 'Samsung',
                     'modelo': 'Galaxy S24', 'cantidad': 1,
                     'equipoId': '', 'listado': False}],
    }, ensure_ascii=False)

    s = Solicitud(
        flujo=Solicitud.FLUJO_F43,
        categoria=Solicitud.CATEGORIA_MOVIL,
        estado=Solicitud.ESTADO_APROBADA,
        solicitante=solicitante,
        equipo_descripcion=datos,
        fecha_resolucion=timezone.now(),
    )
    s.save()
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo Factura
# ═══════════════════════════════════════════════════════════════════════════════
class FacturaModelTest(TestCase):

    def setUp(self):
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'fa_pn')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'fa_dir')
        self.solicitud = crear_solicitud(self.persona)

    def test_generar_factura_crea_factura(self):
        """generar_factura crea una factura correctamente."""
        f = generar_factura(self.solicitud, self.directivo)
        self.assertIsNotNone(f.pk)
        self.assertEqual(f.solicitud, self.solicitud)

    def test_numero_factura_formato_correcto(self):
        """El número de factura se genera con formato FAC-YYYY-NNNNN."""
        f = generar_factura(self.solicitud, self.directivo)
        self.assertRegex(f.numero, r'^FAC-\d{4}-\d{5}$')

    def test_generar_factura_no_duplica(self):
        """Llamar generar_factura dos veces no crea dos facturas."""
        generar_factura(self.solicitud, self.directivo)
        generar_factura(self.solicitud, self.directivo)
        self.assertEqual(
            Factura.objects.filter(solicitud=self.solicitud).count(), 1
        )

    def test_estado_pendiente_por_defecto(self):
        """Una factura nueva está pendiente de pago por defecto."""
        f = generar_factura(self.solicitud, self.directivo)
        self.assertEqual(f.estado, Factura.ESTADO_PENDIENTE)
        self.assertFalse(f.esta_pagada)

    def test_registrar_pago_cambia_estado(self):
        """Al registrar el pago la factura pasa a pagada."""
        f = generar_factura(self.solicitud, self.directivo)
        registrar_pago(f, self.directivo)
        f.refresh_from_db()
        self.assertEqual(f.estado, Factura.ESTADO_PAGADA)
        self.assertTrue(f.esta_pagada)

    def test_registrar_pago_genera_licencia(self):
        """Al registrar el pago se genera la licencia automáticamente."""
        f = generar_factura(self.solicitud, self.directivo)
        registrar_pago(f, self.directivo)
        self.assertTrue(
            Licencia.objects.filter(solicitud=self.solicitud).exists()
        )

    def test_clase_badge_factura(self):
        """clase_badge retorna la clase correcta según el estado."""
        f = generar_factura(self.solicitud, self.directivo)
        self.assertEqual(f.clase_badge, 'badge-pendiente')
        registrar_pago(f, self.directivo)
        f.refresh_from_db()
        self.assertEqual(f.clase_badge, 'badge-aprobado')


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo Licencia
# ═══════════════════════════════════════════════════════════════════════════════
class LicenciaModelTest(TestCase):

    def setUp(self):
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'li_pn')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'li_dir')
        self.solicitud = crear_solicitud(self.persona)

    def test_numero_generado_automaticamente(self):
        """El número de licencia se genera automáticamente con formato correcto."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertRegex(l.numero, r'^LIC-\d{4}-\d{5}$')

    def test_estado_vigente_por_defecto(self):
        """Una licencia nueva está vigente por defecto."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertEqual(l.estado, Licencia.ESTADO_VIGENTE)

    def test_relacion_con_solicitud(self):
        """La licencia está relacionada correctamente con la solicitud."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertEqual(l.solicitud, self.solicitud)

    def test_str_licencia(self):
        """El __str__ incluye el número y el estado."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertIn(l.numero, str(l))

    def test_numeros_unicos(self):
        """Dos licencias no pueden tener el mismo número."""
        s2 = crear_solicitud(crear_usuario(
            Usuario.ROL_PERSONA_NATURAL, 'li_pn2'
        ))
        l1 = generar_licencia(self.solicitud, self.directivo)
        l2 = generar_licencia(s2, self.directivo)
        self.assertNotEqual(l1.numero, l2.numero)

    def test_generar_licencia_no_duplica(self):
        """Llamar generar_licencia dos veces no crea dos licencias."""
        generar_licencia(self.solicitud, self.directivo)
        generar_licencia(self.solicitud, self.directivo)
        self.assertEqual(
            Licencia.objects.filter(solicitud=self.solicitud).count(), 1
        )

    def test_licencia_definitiva_sin_vencimiento(self):
        """Una licencia definitiva no tiene fecha de vencimiento."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertIsNone(l.fecha_vencimiento)
        self.assertFalse(l.es_temporal)

    def test_licencia_temporal_con_vencimiento(self):
        """Una licencia temporal tiene fecha de vencimiento calculada."""
        s = crear_solicitud(self.persona, periodo='temporal', meses='6')
        l = generar_licencia(s, self.directivo)
        self.assertIsNotNone(l.fecha_vencimiento)
        self.assertTrue(l.es_temporal)

    def test_licencia_temporal_6_meses(self):
        """La fecha de vencimiento de 6 meses es correcta."""
        s = crear_solicitud(self.persona, periodo='temporal', meses='6')
        l = generar_licencia(s, self.directivo)
        esperada = date.today().replace(
            month=((date.today().month - 1 + 6) % 12) + 1
        )
        diferencia = abs((l.fecha_vencimiento - date.today()).days)
        self.assertGreater(diferencia, 150)
        self.assertLess(diferencia, 200)

    def test_es_vigente_sin_vencimiento(self):
        """Una licencia definitiva vigente es_vigente = True."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertTrue(l.es_vigente)

    def test_es_vigente_temporal_no_vencida(self):
        """Una licencia temporal no vencida es_vigente = True."""
        s = crear_solicitud(self.persona, periodo='temporal', meses='6')
        l = generar_licencia(s, self.directivo)
        self.assertTrue(l.es_vigente)

    def test_verificar_vencimiento_actualiza_estado(self):
        """verificar_vencimiento actualiza el estado si la fecha venció."""
        s = crear_solicitud(self.persona, periodo='temporal', meses='6')
        l = generar_licencia(s, self.directivo)
        l.fecha_vencimiento = date.today() - timedelta(days=1)
        l.save()
        l.verificar_vencimiento()
        self.assertEqual(l.estado, Licencia.ESTADO_VENCIDA)

    def test_clase_badge_vigente(self):
        """clase_badge retorna badge-aprobado para licencia vigente."""
        l = generar_licencia(self.solicitud, self.directivo)
        self.assertEqual(l.clase_badge, 'badge-aprobado')

    def test_clase_badge_revocada(self):
        """clase_badge retorna badge-denegado para licencia revocada."""
        l = generar_licencia(self.solicitud, self.directivo)
        l.estado = Licencia.ESTADO_REVOCADA
        l.save()
        self.assertEqual(l.clase_badge, 'badge-denegado')


# ═══════════════════════════════════════════════════════════════════════════════
# Vistas de licencias
# ═══════════════════════════════════════════════════════════════════════════════
class LicenciaVistaTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.persona1  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'lv_pn1')
        self.persona2  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'lv_pn2')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'lv_dir')
        self.solicitud = crear_solicitud(self.persona1)
        self.licencia  = generar_licencia(self.solicitud, self.directivo)

    def test_lista_sin_autenticar_redirige(self):
        """Sin autenticación redirige al login."""
        r = self.client.get(reverse('licencias:lista'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_lista_licencias_accesible_para_persona(self):
        """Persona natural puede ver su lista de licencias."""
        self.client.login(username='lv_pn1', password='test1234')
        r = self.client.get(reverse('licencias:lista'))
        self.assertEqual(r.status_code, 200)

    def test_lista_licencias_persona_solo_ve_las_suyas(self):
        """Persona natural solo ve sus propias licencias."""
        self.client.login(username='lv_pn2', password='test1234')
        r = self.client.get(reverse('licencias:lista'))
        self.assertEqual(r.status_code, 200)
        for l in r.context['licencias']:
            self.assertEqual(l.solicitud.solicitante, self.persona2)

    def test_lista_licencias_directivo_ve_todas(self):
        """El directivo ve todas las licencias."""
        self.client.login(username='lv_dir', password='test1234')
        r = self.client.get(reverse('licencias:lista'))
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.context['licencias']), 1)

    def test_detalle_licencia_accesible_para_solicitante(self):
        """El solicitante puede ver el detalle de su licencia."""
        self.client.login(username='lv_pn1', password='test1234')
        r = self.client.get(
            reverse('licencias:detalle', args=[self.licencia.numero])
        )
        self.assertEqual(r.status_code, 200)

    def test_detalle_licencia_denegado_para_otra_persona(self):
        """Otra persona no puede ver la licencia de alguien más."""
        self.client.login(username='lv_pn2', password='test1234')
        r = self.client.get(
            reverse('licencias:detalle', args=[self.licencia.numero])
        )
        self.assertEqual(r.status_code, 302)

    def test_detalle_licencia_accesible_para_directivo(self):
        """El directivo puede ver cualquier licencia."""
        self.client.login(username='lv_dir', password='test1234')
        r = self.client.get(
            reverse('licencias:detalle', args=[self.licencia.numero])
        )
        self.assertEqual(r.status_code, 200)

    def test_filtro_por_estado_vigente(self):
        """El filtro por estado funciona correctamente."""
        self.client.login(username='lv_dir', password='test1234')
        r = self.client.get(reverse('licencias:lista'), {'estado': 'vigente'})
        self.assertEqual(r.status_code, 200)
        for l in r.context['licencias']:
            self.assertEqual(l.estado, Licencia.ESTADO_VIGENTE)

    def test_revocar_licencia_solo_directivo(self):
        """Solo el directivo puede revocar una licencia."""
        self.client.login(username='lv_dir', password='test1234')
        self.client.post(
            reverse('licencias:revocar', args=[self.licencia.numero]),
            {'motivo': 'Prueba de revocación'}
        )
        self.licencia.refresh_from_db()
        self.assertEqual(self.licencia.estado, Licencia.ESTADO_REVOCADA)

    def test_revocar_licencia_denegado_para_persona_natural(self):
        """Persona natural no puede revocar licencias."""
        self.client.login(username='lv_pn1', password='test1234')
        self.client.post(
            reverse('licencias:revocar', args=[self.licencia.numero]),
            {'motivo': 'Intento no autorizado'}
        )
        self.licencia.refresh_from_db()
        self.assertEqual(self.licencia.estado, Licencia.ESTADO_VIGENTE)

    def test_revocar_sin_motivo_no_revoca(self):
        """Revocar sin especificar motivo no cambia el estado."""
        self.client.login(username='lv_dir', password='test1234')
        self.client.post(
            reverse('licencias:revocar', args=[self.licencia.numero]),
            {'motivo': ''}
        )
        self.licencia.refresh_from_db()
        self.assertEqual(self.licencia.estado, Licencia.ESTADO_VIGENTE)


# ═══════════════════════════════════════════════════════════════════════════════
# Vistas de facturas
# ═══════════════════════════════════════════════════════════════════════════════
class FacturaVistaTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'fv_pn')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'fv_dir')
        self.solicitud = crear_solicitud(self.persona)
        self.factura   = generar_factura(self.solicitud, self.directivo)

    def test_lista_facturas_accesible_para_directivo(self):
        """El directivo puede ver la lista de facturas."""
        self.client.login(username='fv_dir', password='test1234')
        r = self.client.get(reverse('licencias:lista_facturas'))
        self.assertEqual(r.status_code, 200)

    def test_lista_facturas_accesible_para_persona(self):
        """La persona natural puede ver sus facturas."""
        self.client.login(username='fv_pn', password='test1234')
        r = self.client.get(reverse('licencias:lista_facturas'))
        self.assertEqual(r.status_code, 200)

    def test_detalle_factura_accesible_para_solicitante(self):
        """El solicitante puede ver el detalle de su factura."""
        self.client.login(username='fv_pn', password='test1234')
        r = self.client.get(
            reverse('licencias:detalle_factura', args=[self.factura.numero])
        )
        self.assertEqual(r.status_code, 200)

    def test_registrar_pago_genera_licencia(self):
        """Al registrar el pago desde la vista se genera la licencia."""
        self.client.login(username='fv_dir', password='test1234')
        self.client.post(
            reverse('licencias:registrar_pago', args=[self.factura.numero]),
            {'observaciones': 'Pago registrado en caja'}
        )
        self.assertTrue(
            Licencia.objects.filter(solicitud=self.solicitud).exists()
        )

    def test_registrar_pago_denegado_para_persona_natural(self):
        """Persona natural no puede registrar pagos."""
        self.client.login(username='fv_pn', password='test1234')
        self.client.post(
            reverse('licencias:registrar_pago', args=[self.factura.numero]),
            {'observaciones': 'Intento no autorizado'}
        )
        self.factura.refresh_from_db()
        self.assertFalse(self.factura.esta_pagada)