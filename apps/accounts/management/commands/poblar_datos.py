"""
Comando de gestión para poblar la base de datos con datos iniciales.

Uso:
    python manage.py poblar_datos
    python manage.py poblar_datos --limpiar    # Limpia todo antes de poblar
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import json

from apps.licencias.models import Licencia, Factura
from apps.notificaciones.models import Notificacion
from apps.solicitudes.models import Solicitud, HistorialSolicitud
from apps.equipos.models import Equipo, CategoriaEquipo
from apps.accounts.models import Usuario
from apps.notificaciones.servicios import notificar_solicitud_nueva
from apps.licencias.servicios import generar_licencia, generar_factura


class Command(BaseCommand):
    help = 'Puebla la base de datos con datos iniciales para desarrollo y pruebas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina todos los datos existentes antes de poblar.',
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            self._limpiar_datos()

        self.stdout.write('\n' + '─' * 60)
        self.stdout.write(self.style.SUCCESS('  UPTCER — Poblando base de datos'))
        self.stdout.write('─' * 60 + '\n')

        with transaction.atomic():
            usuarios   = self._crear_usuarios()
            categorias = self._crear_categorias()
            equipos    = self._crear_equipos(categorias)
            solicitudes = self._crear_solicitudes(usuarios, equipos)
            self._crear_facturas_y_licencias(solicitudes, usuarios)

        self.stdout.write('\n' + '─' * 60)
        self.stdout.write(self.style.SUCCESS('  Base de datos poblada correctamente.'))
        self.stdout.write('─' * 60 + '\n')

    # ─── Limpiar ──────────────────────────────────────────────────────────────
    def _limpiar_datos(self):
        self.stdout.write(self.style.WARNING('Limpiando datos existentes...'))
        Licencia.objects.all().delete()
        Factura.objects.all().delete()
        Notificacion.objects.all().delete()
        HistorialSolicitud.objects.all().delete()
        Solicitud.objects.all().delete()
        Equipo.objects.all().delete()
        CategoriaEquipo.objects.all().delete()
        Usuario.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('Datos eliminados.\n'))

    # ─── Usuarios ─────────────────────────────────────────────────────────────
    def _crear_usuarios(self):
        self.stdout.write('Creando usuarios...')

        usuarios = {}

        datos_usuarios = [
            # Directivo
            {
                'username':  'directivo',
                'email':     'directivo@mincom.cu',
                'nombre':    'Carlos',
                'apellidos': 'Rodríguez Pérez',
                'rol':       Usuario.ROL_DIRECTIVO,
                'telefono':  '+53 7 838 0000',
                'password':  'directivo123',
            },
            # Especialistas de área
            {
                'username':  'esp_radiofaro',
                'email':     'radiofaro@mincom.cu',
                'nombre':    'María',
                'apellidos': 'González López',
                'rol':       Usuario.ROL_ESPECIALISTA_RADIOFARO,
                'telefono':  '+53 7 838 0001',
                'password':  'especialista123',
            },
            {
                'username':  'esp_movil',
                'email':     'movil@mincom.cu',
                'nombre':    'Roberto',
                'apellidos': 'Fernández García',
                'rol':       Usuario.ROL_ESPECIALISTA_MOVIL,
                'telefono':  '+53 7 838 0002',
                'password':  'especialista123',
            },
            {
                'username':  'esp_maritimo',
                'email':     'maritimo@mincom.cu',
                'nombre':    'Ana',
                'apellidos': 'Martínez Suárez',
                'rol':       Usuario.ROL_ESPECIALISTA_MARITIMO,
                'telefono':  '+53 7 838 0003',
                'password':  'especialista123',
            },
            {
                'username':  'esp_internet',
                'email':     'internet@mincom.cu',
                'nombre':    'Pedro',
                'apellidos': 'Herrera Domínguez',
                'rol':       Usuario.ROL_ESPECIALISTA_INTERNET,
                'telefono':  '+53 7 838 0004',
                'password':  'especialista123',
            },
            # Especialista superior
            {
                'username':  'esp_superior',
                'email':     'superior@mincom.cu',
                'nombre':    'Luis',
                'apellidos': 'Ramírez Castro',
                'rol':       Usuario.ROL_ESPECIALISTA_SUPERIOR,
                'telefono':  '+53 7 838 0005',
                'password':  'superior123',
            },
            # Aduana
            {
                'username':  'aduana',
                'email':     'aduana@aduana.cu',
                'nombre':    'Elena',
                'apellidos': 'Torres Vidal',
                'rol':       Usuario.ROL_ADUANA,
                'telefono':  '+53 7 266 0000',
                'password':  'aduana123',
            },
            # Personas naturales
            {
                'username':  'persona1',
                'email':     'juan.perez@nauta.cu',
                'nombre':    'Juan',
                'apellidos': 'Pérez Morales',
                'rol':       Usuario.ROL_PERSONA_NATURAL,
                'telefono':  '+53 5 234 5678',
                'password':  'persona123',
            },
            {
                'username':  'persona2',
                'email':     'maria.lopez@nauta.cu',
                'nombre':    'María',
                'apellidos': 'López Fuentes',
                'rol':       Usuario.ROL_PERSONA_NATURAL,
                'telefono':  '+53 5 345 6789',
                'password':  'persona123',
            },
            {
                'username':  'persona3',
                'email':     'pedro.garcia@nauta.cu',
                'nombre':    'Pedro',
                'apellidos': 'García Ramos',
                'rol':       Usuario.ROL_PERSONA_NATURAL,
                'telefono':  '+53 5 456 7890',
                'password':  'persona123',
            },
        ]

        for datos in datos_usuarios:
            usuario, creado = Usuario.objects.get_or_create(
                username=datos['username'],
                defaults={
                    'email':     datos['email'],
                    'nombre':    datos['nombre'],
                    'apellidos': datos['apellidos'],
                    'rol':       datos['rol'],
                    'telefono':  datos['telefono'],
                }
            )
            if creado:
                usuario.set_password(datos['password'])
                usuario.save()
                self.stdout.write(
                    f'  {self.style.SUCCESS("+")} {usuario.get_nombre_completo()} '
                    f'({usuario.get_rol_display()}) — '
                    f'usuario: {usuario.username} / contraseña: {datos["password"]}'
                )
            else:
                self.stdout.write(
                    f'  {self.style.WARNING("~")} {usuario.username} ya existe, omitiendo.'
                )
            usuarios[datos['username']] = usuario

        return usuarios

    # ─── Categorías de equipos ────────────────────────────────────────────────
    def _crear_categorias(self):
        self.stdout.write('\nCreando categorías de equipos...')

        datos_categorias = [
            ('Teléfonos móviles',       'Dispositivos de comunicación móvil celular.'),
            ('Routers y access points', 'Equipos de enrutamiento y puntos de acceso inalámbrico.'),
            ('Tablets y computadoras',  'Tablets, laptops y computadoras con conectividad inalámbrica.'),
            ('Equipos de radio',        'Radios de comunicación, walkie-talkies y equipos de radiofrecuencia.'),
            ('Cámaras y vigilancia',    'Cámaras IP, sistemas de videovigilancia con conectividad de red.'),
            ('Wearables y accesorios',  'Relojes inteligentes, audífonos bluetooth y accesorios inalámbricos.'),
            ('Equipos satelitales',     'Receptores GPS, antenas satelitales y equipos de comunicación satelital.'),
            ('Modems y equipos de red', 'Módems, switches, y equipos de infraestructura de red.'),
        ]

        categorias = {}
        for nombre, descripcion in datos_categorias:
            cat, creado = CategoriaEquipo.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
            estado = self.style.SUCCESS('+') if creado else self.style.WARNING('~')
            self.stdout.write(f'  {estado} {nombre}')
            categorias[nombre] = cat

        return categorias

    # ─── Equipos ──────────────────────────────────────────────────────────────
    def _crear_equipos(self, categorias):
        self.stdout.write('\nCreando catálogo de equipos...')

        datos_equipos = [
            {
                'categoria':        'Teléfonos móviles',
                'nombre':           'Teléfono inteligente de gama alta',
                'marca':            'Samsung',
                'modelo':           'Galaxy S24',
                'descripcion':      'Teléfono inteligente con conectividad 5G, WiFi 6 y Bluetooth 5.3.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Teléfonos móviles',
                'nombre':           'Teléfono inteligente',
                'marca':            'Apple',
                'modelo':           'iPhone 15',
                'descripcion':      'Teléfono inteligente con chip A16, WiFi 6 y Bluetooth 5.3.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Teléfonos móviles',
                'nombre':           'Teléfono inteligente económico',
                'marca':            'Xiaomi',
                'modelo':           'Redmi Note 13',
                'descripcion':      'Teléfono inteligente de gama media con WiFi dual band.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Routers y access points',
                'nombre':           'Router inalámbrico doméstico',
                'marca':            'TP-Link',
                'modelo':           'Archer AX55',
                'descripcion':      'Router WiFi 6 AX3000, dual band 2.4/5 GHz para uso doméstico.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Routers y access points',
                'nombre':           'Router empresarial',
                'marca':            'Cisco',
                'modelo':           'RV340',
                'descripcion':      'Router VPN empresarial con gestión avanzada de red.',
                'banda_frecuencia': 'restringida',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Equipos de radio',
                'nombre':           'Radio portátil profesional',
                'marca':            'Motorola',
                'modelo':           'DP4400e',
                'descripcion':      'Radio digital MOTOTRBO para comunicaciones profesionales UHF/VHF.',
                'banda_frecuencia': 'restringida',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Wearables y accesorios',
                'nombre':           'Audífonos inalámbricos',
                'marca':            'Sony',
                'modelo':           'WH-1000XM5',
                'descripcion':      'Audífonos over-ear con cancelación de ruido y Bluetooth 5.2.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': False,
            },
            {
                'categoria':        'Equipos satelitales',
                'nombre':           'Terminal VSAT',
                'marca':            'Hughes',
                'modelo':           'HT2000W',
                'descripcion':      'Terminal satelital VSAT para conectividad de banda ancha.',
                'banda_frecuencia': 'restringida',
                'requiere_permiso': True,
            },
        ]

        equipos = {}
        for datos in datos_equipos:
            cat = categorias.get(datos['categoria'])
            if not cat:
                continue
            equipo, creado = Equipo.objects.get_or_create(
                marca=datos['marca'],
                modelo=datos['modelo'],
                defaults={
                    'categoria':        cat,
                    'nombre':           datos['nombre'],
                    'descripcion':      datos['descripcion'],
                    'banda_frecuencia': datos['banda_frecuencia'],
                    'requiere_permiso': datos['requiere_permiso'],
                    'activo':           True,
                }
            )
            estado = self.style.SUCCESS('+') if creado else self.style.WARNING('~')
            self.stdout.write(f'  {estado} {datos["marca"]} {datos["modelo"]}')
            equipos[f'{datos["marca"]}_{datos["modelo"]}'] = equipo

        return equipos

    # ─── Solicitudes ──────────────────────────────────────────────────────────
    def _crear_solicitudes(self, usuarios, equipos):
        self.stdout.write('\nCreando solicitudes de ejemplo...')

        persona1     = usuarios.get('persona1')
        persona2     = usuarios.get('persona2')
        persona3     = usuarios.get('persona3')
        esp_movil    = usuarios.get('esp_movil')
        esp_internet = usuarios.get('esp_internet')
        esp_superior = usuarios.get('esp_superior')

        def datos_f43(persona, provincia, modo, equipo_desc, marca, modelo,
                      cantidad=1, objetivo='empleo_directo', periodo='definitiva',
                      vuelo='', fecha_arribo='', pais='México', rad='', meses='',
                      equipo_id=None):
            return json.dumps({
                'nombre_apellidos':       persona.get_nombre_completo(),
                'numero_pasaporte':       'A12345678',
                'pais_residencia':        'Cuba',
                'direccion_residencia':   'Calle 23 e/ J e I, Vedado, La Habana',
                'correo_electronico':     persona.email,
                'telefono':               persona.telefono,
                'provincia':              provincia,
                'modo_importacion':       modo,
                'numero_vuelo':           vuelo,
                'fecha_arribo':           fecha_arribo,
                'pais_procedencia':       pais,
                'aduana_acceso':          'Aeropuerto',
                'lugar_acceso':           'Aeropuerto Internacional José Martí',
                'numero_rad':             rad,
                'objetivo_importacion':   objetivo,
                'objetivo_otros_detalle': '',
                'periodo_importacion':    periodo,
                'tiempo_solicitado':      meses,
                'firma_ci':               '90123456789',
                'fecha_solicitud':        timezone.now().date().isoformat(),
                'equipos': [{
                    'descripcion': equipo_desc,
                    'marca':       marca,
                    'modelo':      modelo,
                    'cantidad':    cantidad,
                    'equipoId':    str(equipo_id) if equipo_id else '',
                    'listado':     bool(equipo_id),
                }],
            }, ensure_ascii=False)

        solicitudes_datos = [
            # 1. Aprobada — Samsung Galaxy S24 — categoría móvil
            {
                'flujo':       Solicitud.FLUJO_F43,
                'categoria':   Solicitud.CATEGORIA_MOVIL,
                'estado':      Solicitud.ESTADO_APROBADA,
                'solicitante': persona1,
                'especialista': esp_movil,
                'descripcion': datos_f43(
                    persona1, 'la_habana', 'equipaje',
                    'Teléfono inteligente de uso personal',
                    'Samsung', 'Galaxy S24', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU101', fecha_arribo='2025-06-10', pais='España',
                    equipo_id=equipos['Samsung_Galaxy S24'].pk
                ),
                'obs': 'Documentación verificada. Equipo en banda libre. Aprobado.',
                'fecha_res': True,
            },
            # 2. Aprobada — iPhone 15 — categoría móvil
            {
                'flujo':       Solicitud.FLUJO_F43,
                'categoria':   Solicitud.CATEGORIA_MOVIL,
                'estado':      Solicitud.ESTADO_APROBADA,
                'solicitante': persona2,
                'especialista': esp_movil,
                'descripcion': datos_f43(
                    persona2, 'santiago_de_cuba', 'equipaje',
                    'Teléfono inteligente Apple',
                    'Apple', 'iPhone 15', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU205', fecha_arribo='2025-06-15', pais='Rusia',
                    equipo_id=equipos['Apple_iPhone 15'].pk
                ),
                'obs': 'Equipo de banda libre. Importación definitiva aprobada.',
                'fecha_res': True,
            },
            # 3. Denegada — Cisco RV340 — categoría internet
            {
                'flujo':       Solicitud.FLUJO_F43,
                'categoria':   Solicitud.CATEGORIA_INTERNET,
                'estado':      Solicitud.ESTADO_DENEGADA,
                'solicitante': persona3,
                'especialista': esp_internet,
                'descripcion': datos_f43(
                    persona3, 'holguin', 'equipaje',
                    'Router empresarial VPN',
                    'Cisco', 'RV340', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU310', fecha_arribo='2025-06-20', pais='México'
                ),
                'obs': 'Equipo con frecuencia restringida. No autorizado para importación por persona natural.',
                'fecha_res': True,
            },
            # 4. En revisión — iPad Pro — categoría internet
            {
                'flujo':       Solicitud.FLUJO_F43,
                'categoria':   Solicitud.CATEGORIA_INTERNET,
                'estado':      Solicitud.ESTADO_EN_REVISION,
                'solicitante': persona1,
                'especialista': esp_internet,
                'descripcion': datos_f43(
                    persona1, 'matanzas', 'equipaje',
                    'Tablet de alta gama para trabajo',
                    'Apple', 'iPad Pro 12.9', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU415', fecha_arribo='2025-07-01', pais='Panamá'
                ),
                'obs': 'En proceso de verificación de documentación.',
                'fecha_res': False,
            },
            # 5. Enviada — Xiaomi Redmi Note 13 — categoría móvil
            {
                'flujo':       Solicitud.FLUJO_F43,
                'categoria':   Solicitud.CATEGORIA_MOVIL,
                'estado':      Solicitud.ESTADO_ENVIADA,
                'solicitante': persona2,
                'especialista': None,
                'descripcion': datos_f43(
                    persona2, 'villa_clara', 'equipaje',
                    'Teléfono inteligente para uso personal',
                    'Xiaomi', 'Redmi Note 13', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU520', fecha_arribo='2025-07-10', pais='México',
                    equipo_id=equipos['Xiaomi_Redmi Note 13'].pk
                ),
                'obs': '',
                'fecha_res': False,
            },
            # 6. Enviada — TP-Link Archer AX55 — categoría internet
            {
                'flujo':       Solicitud.FLUJO_F43,
                'categoria':   Solicitud.CATEGORIA_INTERNET,
                'estado':      Solicitud.ESTADO_ENVIADA,
                'solicitante': persona3,
                'especialista': None,
                'descripcion': datos_f43(
                    persona3, 'camaguey', 'rad',
                    'Router WiFi doméstico',
                    'TP-Link', 'Archer AX55', 1, 'empleo_directo', 'definitiva',
                    rad='RAD-2025-001234', equipo_id=equipos['TP-Link_Archer AX55'].pk
                ),
                'obs': '',
                'fecha_res': False,
            },
            # 7. Pendiente de aprobación — equipo no listado evaluado por superior
            {
                'flujo':             Solicitud.FLUJO_F43,
                'categoria':         Solicitud.CATEGORIA_MOVIL,
                'estado':            Solicitud.ESTADO_PENDIENTE_APROBACION,
                'solicitante':       persona2,
                'especialista':      esp_superior,
                'equipo_no_listado': True,
                'marca_manual':      'DJI',
                'modelo_manual':     'Mini 4 Pro',
                'descripcion': datos_f43(
                    persona2, 'pinar_del_rio', 'equipaje',
                    'Dron de fotografía aérea con control remoto inalámbrico',
                    'DJI', 'Mini 4 Pro', 1, 'otros', 'definitiva',
                    vuelo='CU740', fecha_arribo='2025-07-05', pais='México'
                ),
                'obs': 'Equipo evaluado por especialista superior. Pendiente de aprobación por directivo.',
                'fecha_res': False,
            },
            # 8. En revisión superior — equipo no listado
            {
                'flujo':             Solicitud.FLUJO_F43,
                'categoria':         Solicitud.CATEGORIA_MARITIMO,
                'estado':            Solicitud.ESTADO_EN_REVISION_SUPERIOR,
                'solicitante':       persona1,
                'especialista':      esp_superior,
                'equipo_no_listado': True,
                'marca_manual':      'Garmin',
                'modelo_manual':     'GPSMAP 78sc',
                'descripcion': datos_f43(
                    persona1, 'la_habana', 'equipaje',
                    'GPS marino portátil con radio VHF integrada',
                    'Garmin', 'GPSMAP 78sc', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU850', fecha_arribo='2025-07-15', pais='España'
                ),
                'obs': 'Equipo no listado en catálogo. Derivado a especialista superior.',
                'fecha_res': False,
            },
        ]

        solicitudes_creadas = []

        for i, datos in enumerate(solicitudes_datos, 1):
            if Solicitud.objects.filter(
                solicitante=datos['solicitante'],
                categoria=datos.get('categoria', ''),
                estado=datos['estado'],
            ).exists():
                self.stdout.write(
                    f'  {self.style.WARNING("~")} Solicitud #{i} ya existe, omitiendo.'
                )
                continue

            solicitud = Solicitud(
                flujo              = datos['flujo'],
                categoria          = datos.get('categoria', ''),
                estado             = datos['estado'],
                solicitante        = datos['solicitante'],
                equipo_descripcion = datos['descripcion'],
                observaciones_tecnicas = datos.get('obs', ''),
                equipo_no_listado      = datos.get('equipo_no_listado', False),
                equipo_marca_manual    = datos.get('marca_manual', ''),
                equipo_modelo_manual   = datos.get('modelo_manual', ''),
            )

            if datos.get('fecha_res'):
                solicitud.fecha_resolucion = timezone.now()

            solicitud.save()

            # Historial — creación
            HistorialSolicitud.objects.create(
                solicitud       = solicitud,
                estado_anterior = '',
                estado_nuevo    = Solicitud.ESTADO_ENVIADA,
                usuario         = datos['solicitante'],
                observacion     = 'Solicitud creada y enviada por el solicitante.',
            )

            # Historial — cambio de estado por especialista
            if datos['estado'] != Solicitud.ESTADO_ENVIADA and datos.get('especialista'):
                HistorialSolicitud.objects.create(
                    solicitud       = solicitud,
                    estado_anterior = Solicitud.ESTADO_ENVIADA,
                    estado_nuevo    = datos['estado'],
                    usuario         = datos['especialista'],
                    observacion     = datos.get('obs', ''),
                )

            solicitudes_creadas.append(solicitud)
            self.stdout.write(
                f'  {self.style.SUCCESS("+")} {solicitud.numero} — '
                f'{solicitud.get_estado_display()} — '
                f'{solicitud.solicitante.get_nombre_completo()} '
                f'[{solicitud.get_categoria_display()}]'
            )

        return solicitudes_creadas

    # ─── Facturas y licencias ─────────────────────────────────────────────────
    def _crear_facturas_y_licencias(self, solicitudes, usuarios):
        self.stdout.write('\nGenerando facturas y licencias...')

        directivo = usuarios.get('directivo')

        for solicitud in solicitudes:
            if solicitud.estado == Solicitud.ESTADO_APROBADA:
                try:
                    factura = generar_factura(solicitud, directivo)
                    factura.estado   = Factura.ESTADO_PAGADA
                    factura.fecha_pago = timezone.now()
                    factura.registrado_pago_por = directivo
                    factura.save()

                    licencia = generar_licencia(solicitud, directivo)
                    self.stdout.write(
                        f'  {self.style.SUCCESS("+")} Factura {factura.numero} + '
                        f'Licencia {licencia.numero} — '
                        f'{solicitud.solicitante.get_nombre_completo()} — '
                        f'{"Temporal" if licencia.es_temporal else "Definitiva"}'
                    )
                except Exception as e:
                    self.stdout.write(
                        f'  {self.style.WARNING("~")} Error en {solicitud.numero}: {e}'
                    )

            elif solicitud.estado == Solicitud.ESTADO_PENDIENTE_APROBACION:
                try:
                    factura = generar_factura(solicitud, directivo)
                    self.stdout.write(
                        f'  {self.style.SUCCESS("+")} Factura {factura.numero} generada '
                        f'(pendiente de pago) — {solicitud.numero}'
                    )
                except Exception as e:
                    self.stdout.write(
                        f'  {self.style.WARNING("~")} Error en {solicitud.numero}: {e}'
                    )