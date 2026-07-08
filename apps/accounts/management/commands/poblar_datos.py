"""
Comando de gestión para poblar la base de datos con datos iniciales.

Uso:
    python manage.py poblar_datos
    python manage.py poblar_datos --limpiar    # Limpia todo antes de poblar
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.licencias.models import Licencia
from apps.notificaciones.models import Notificacion
from apps.solicitudes.models import Solicitud, HistorialSolicitud
from apps.equipos.models import Equipo, CategoriaEquipo
from apps.accounts.models import Usuario
from apps.notificaciones.servicios import notificar_solicitud_nueva
from apps.licencias.servicios import generar_licencia


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
            usuarios    = self._crear_usuarios()
            categorias  = self._crear_categorias()
            equipos     = self._crear_equipos(categorias)
            solicitudes = self._crear_solicitudes(usuarios, equipos)
            self._crear_licencias(solicitudes, usuarios)

        self.stdout.write('\n' + '─' * 60)
        self.stdout.write(self.style.SUCCESS('  Base de datos poblada correctamente.'))
        self.stdout.write('─' * 60 + '\n')

    # ─── Limpiar ──────────────────────────────────────────────────────────────
    def _limpiar_datos(self):

        self.stdout.write(self.style.WARNING('Limpiando datos existentes...'))
        Licencia.objects.all().delete()
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
            {
                'username':  'directivo',
                'email':     'directivo@mincom.cu',
                'nombre':    'Carlos',
                'apellidos': 'Rodríguez Pérez',
                'rol':       Usuario.ROL_DIRECTIVO,
                'telefono':  '+53 7 838 0000',
                'password':  'directivo123',
            },
            {
                'username':  'operador1',
                'email':     'operador1@mincom.cu',
                'nombre':    'María',
                'apellidos': 'González López',
                'rol':       Usuario.ROL_OPERADOR,
                'telefono':  '+53 7 838 0001',
                'password':  'operador123',
            },
            {
                'username':  'operador2',
                'email':     'operador2@mincom.cu',
                'nombre':    'Roberto',
                'apellidos': 'Fernández García',
                'rol':       Usuario.ROL_OPERADOR,
                'telefono':  '+53 7 838 0002',
                'password':  'operador123',
            },
            {
                'username':  'especialista',
                'email':     'especialista@mincom.cu',
                'nombre':    'Ana',
                'apellidos': 'Martínez Suárez',
                'rol':       Usuario.ROL_ESPECIALISTA,
                'telefono':  '+53 7 838 0003',
                'password':  'especialista123',
            },
            {
                'username':  'aduana',
                'email':     'aduana@aduana.cu',
                'nombre':    'Luis',
                'apellidos': 'Herrera Domínguez',
                'rol':       Usuario.ROL_ADUANA,
                'telefono':  '+53 7 266 0000',
                'password':  'aduana123',
            },
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
                username = datos['username'],
                defaults = {
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
                    f'({usuario.get_rol_display()}) — usuario: {usuario.username} / '
                    f'contraseña: {datos["password"]}'
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
            ('Teléfonos móviles',         'Dispositivos de comunicación móvil celular.'),
            ('Routers y access points',   'Equipos de enrutamiento y puntos de acceso inalámbrico.'),
            ('Tablets y computadoras',    'Tablets, laptops y computadoras personales con conectividad inalámbrica.'),
            ('Equipos de radio',          'Radios de comunicación, walkie-talkies y equipos de radiofrecuencia.'),
            ('Cámaras y vigilancia',      'Cámaras IP, sistemas de videovigilancia con conectividad de red.'),
            ('Wearables y accesorios',    'Relojes inteligentes, audífonos bluetooth y accesorios inalámbricos.'),
            ('Equipos satelitales',       'Receptores GPS, antenas satelitales y equipos de comunicación satelital.'),
            ('Modems y equipos de red',   'Módems, switches, y equipos de infraestructura de red.'),
        ]

        categorias = {}
        for nombre, descripcion in datos_categorias:
            cat, creado = CategoriaEquipo.objects.get_or_create(
                nombre      = nombre,
                defaults    = {'descripcion': descripcion}
            )
            estado = self.style.SUCCESS('+') if creado else self.style.WARNING('~')
            self.stdout.write(f'  {estado} {nombre}')
            categorias[nombre] = cat

        return categorias

    # ─── Equipos ──────────────────────────────────────────────────────────────
    def _crear_equipos(self, categorias):

        self.stdout.write('\nCreando catálogo de equipos...')

        datos_equipos = [
            # Teléfonos móviles — banda libre
            {
                'categoria':        'Teléfonos móviles',
                'nombre':           'Teléfono inteligente de gama alta',
                'marca':            'Samsung',
                'modelo':           'Galaxy S24',
                'descripcion':      'Teléfono inteligente con conectividad 5G, WiFi 6 (2.4/5 GHz) y Bluetooth 5.3.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Teléfonos móviles',
                'nombre':           'Teléfono inteligente',
                'marca':            'Apple',
                'modelo':           'iPhone 15',
                'descripcion':      'Teléfono inteligente con chip A16, WiFi 6 (2.4/5 GHz) y Bluetooth 5.3.',
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
                'categoria':        'Teléfonos móviles',
                'nombre':           'Teléfono inteligente',
                'marca':            'Huawei',
                'modelo':           'P60 Pro',
                'descripcion':      'Teléfono con cámara avanzada y WiFi 6 dual band.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            # Routers — algunos libres, algunos restringidos
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
                'categoria':        'Routers y access points',
                'nombre':           'Access point empresarial',
                'marca':            'Ubiquiti',
                'modelo':           'UniFi AP AC Pro',
                'descripcion':      'Punto de acceso inalámbrico de alta densidad para entornos empresariales.',
                'banda_frecuencia': 'restringida',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Routers y access points',
                'nombre':           'Router WiFi doméstico',
                'marca':            'D-Link',
                'modelo':           'DIR-842',
                'descripcion':      'Router WiFi AC1200 dual band para uso doméstico.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            # Tablets y computadoras
            {
                'categoria':        'Tablets y computadoras',
                'nombre':           'Tablet de alta gama',
                'marca':            'Apple',
                'modelo':           'iPad Pro 12.9',
                'descripcion':      'Tablet con chip M2, WiFi 6E y conectividad celular opcional.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Tablets y computadoras',
                'nombre':           'Tablet Android',
                'marca':            'Samsung',
                'modelo':           'Galaxy Tab S9',
                'descripcion':      'Tablet Android de alta gama con WiFi 6E y DeX mode.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Tablets y computadoras',
                'nombre':           'Laptop ultrabook',
                'marca':            'Lenovo',
                'modelo':           'ThinkPad X1 Carbon',
                'descripcion':      'Laptop empresarial con WiFi 6E y Bluetooth 5.2.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            # Equipos de radio — restringidos
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
                'categoria':        'Equipos de radio',
                'nombre':           'Walkie-talkie civil',
                'marca':            'Baofeng',
                'modelo':           'UV-5R',
                'descripcion':      'Radio dual band VHF/UHF de uso general.',
                'banda_frecuencia': 'restringida',
                'requiere_permiso': True,
            },
            # Cámaras y vigilancia
            {
                'categoria':        'Cámaras y vigilancia',
                'nombre':           'Cámara IP doméstica',
                'marca':            'Hikvision',
                'modelo':           'DS-2CD2143G2-I',
                'descripcion':      'Cámara IP domo 4MP con WiFi 2.4 GHz e infrarrojo.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Cámaras y vigilancia',
                'nombre':           'Cámara de seguridad WiFi',
                'marca':            'Dahua',
                'modelo':           'IPC-F42FEP-D',
                'descripcion':      'Cámara fisheye 4MP con WiFi dual band.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            # Wearables
            {
                'categoria':        'Wearables y accesorios',
                'nombre':           'Reloj inteligente',
                'marca':            'Apple',
                'modelo':           'Watch Series 9',
                'descripcion':      'Reloj inteligente con GPS, WiFi 2.4/5 GHz y Bluetooth 5.3.',
                'banda_frecuencia': 'libre',
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
            # Equipos satelitales — restringidos
            {
                'categoria':        'Equipos satelitales',
                'nombre':           'Terminal VSAT',
                'marca':            'Hughes',
                'modelo':           'HT2000W',
                'descripcion':      'Terminal satelital VSAT para conectividad de banda ancha.',
                'banda_frecuencia': 'restringida',
                'requiere_permiso': True,
            },
            # Modems
            {
                'categoria':        'Modems y equipos de red',
                'nombre':           'Módem ADSL/VDSL',
                'marca':            'ZTE',
                'modelo':           'H267N',
                'descripcion':      'Módem router ADSL2+/VDSL2 con WiFi dual band.',
                'banda_frecuencia': 'libre',
                'requiere_permiso': True,
            },
            {
                'categoria':        'Modems y equipos de red',
                'nombre':           'Switch gestionable',
                'marca':            'TP-Link',
                'modelo':           'TL-SG108E',
                'descripcion':      'Switch Gigabit de 8 puertos gestionable.',
                'banda_frecuencia': 'no_aplica',
                'requiere_permiso': False,
            },
        ]

        equipos = {}
        for datos in datos_equipos:
            cat = categorias.get(datos['categoria'])
            if not cat:
                continue
            equipo, creado = Equipo.objects.get_or_create(
                marca  = datos['marca'],
                modelo = datos['modelo'],
                defaults = {
                    'categoria':        cat,
                    'nombre':           datos['nombre'],
                    'descripcion':      datos['descripcion'],
                    'banda_frecuencia': datos['banda_frecuencia'],
                    'requiere_permiso': datos['requiere_permiso'],
                    'activo':           True,
                }
            )
            estado = self.style.SUCCESS('+') if creado else self.style.WARNING('~')
            banda  = {
                'libre':       '📶 Libre',
                'restringida': '🔒 Restringida',
                'no_aplica':   '—',
            }.get(datos['banda_frecuencia'], '')
            self.stdout.write(f'  {estado} {datos["marca"]} {datos["modelo"]} [{banda}]')
            equipos[f'{datos["marca"]}_{datos["modelo"]}'] = equipo

        return equipos

    # ─── Solicitudes ──────────────────────────────────────────────────────────
    def _crear_solicitudes(self, usuarios, equipos):
        import json

        self.stdout.write('\nCreando solicitudes de ejemplo...')

        persona1  = usuarios.get('persona1')
        persona2  = usuarios.get('persona2')
        persona3  = usuarios.get('persona3')
        operador1 = usuarios.get('operador1')
        operador2 = usuarios.get('operador2')

        def datos_f43(persona, provincia, modo, equipo_desc, marca, modelo,
                      cantidad=1, objetivo='empleo_directo', periodo='definitiva',
                      vuelo='', fecha_arribo='', pais='México', aduana='Aeropuerto',
                      lugar='Aeropuerto Internacional José Martí', rad='', meses=''):
            return json.dumps({
                'nombre_apellidos':    persona.get_nombre_completo(),
                'numero_pasaporte':    'A12345678',
                'pais_residencia':     'Cuba',
                'direccion_residencia':'Calle 23 e/ J e I, Vedado, La Habana',
                'correo_electronico':  persona.email,
                'telefono':            persona.telefono,
                'provincia':           provincia,
                'modo_importacion':    modo,
                'numero_vuelo':        vuelo,
                'fecha_arribo':        fecha_arribo,
                'pais_procedencia':    pais,
                'aduana_acceso':       aduana,
                'lugar_acceso':        lugar,
                'numero_rad':          rad,
                'objetivo_importacion': objetivo,
                'objetivo_otros_detalle': '',
                'periodo_importacion': periodo,
                'tiempo_solicitado':   meses,
                'firma_ci':            '90123456789',
                'fecha_solicitud':     timezone.now().date().isoformat(),
                'equipos': [{
                    'descripcion': equipo_desc,
                    'marca':       marca,
                    'modelo':      modelo,
                    'cantidad':    cantidad,
                    'equipoId':    '',
                    'listado':     False,
                }],
            }, ensure_ascii=False)

        solicitudes_datos = [
            # 1. Aprobada — Samsung Galaxy S24
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_APROBADA,
                'solicitante':  persona1,
                'operador':     operador1,
                'descripcion':  datos_f43(
                    persona1, 'la_habana', 'equipaje',
                    'Teléfono inteligente de uso personal',
                    'Samsung', 'Galaxy S24', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU101', fecha_arribo='2025-06-10', pais='España'
                ),
                'obs_operador': 'Documentación verificada. Equipo en banda libre. Aprobado.',
                'fecha_res':    True,
            },
            # 2. Aprobada — iPhone 15
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_APROBADA,
                'solicitante':  persona2,
                'operador':     operador1,
                'descripcion':  datos_f43(
                    persona2, 'santiago_de_cuba', 'equipaje',
                    'Teléfono inteligente Apple',
                    'Apple', 'iPhone 15', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU205', fecha_arribo='2025-06-15', pais='Rusia'
                ),
                'obs_operador': 'Equipo de banda libre. Importación definitiva aprobada.',
                'fecha_res':    True,
            },
            # 3. Denegada — Cisco RV340 (restringida)
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_DENEGADA,
                'solicitante':  persona3,
                'operador':     operador2,
                'descripcion':  datos_f43(
                    persona3, 'holguin', 'equipaje',
                    'Router empresarial VPN',
                    'Cisco', 'RV340', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU310', fecha_arribo='2025-06-20', pais='México'
                ),
                'obs_operador': 'Equipo con frecuencia restringida. No autorizado para importación por persona natural.',
                'fecha_res':    True,
            },
            # 4. En revisión — Apple iPad Pro
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_EN_REVISION,
                'solicitante':  persona1,
                'operador':     operador1,
                'descripcion':  datos_f43(
                    persona1, 'matanzas', 'equipaje',
                    'Tablet de alta gama para trabajo',
                    'Apple', 'iPad Pro 12.9', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU415', fecha_arribo='2025-07-01', pais='Panamá'
                ),
                'obs_operador': 'En proceso de verificación de documentación.',
                'fecha_res':    False,
            },
            # 5. Enviada — Xiaomi Redmi Note 13
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_ENVIADA,
                'solicitante':  persona2,
                'operador':     None,
                'descripcion':  datos_f43(
                    persona2, 'villa_clara', 'equipaje',
                    'Teléfono inteligente para uso personal',
                    'Xiaomi', 'Redmi Note 13', 1, 'empleo_directo', 'definitiva',
                    vuelo='CU520', fecha_arribo='2025-07-10', pais='México'
                ),
                'obs_operador': '',
                'fecha_res':    False,
            },
            # 6. Enviada — TP-Link Archer AX55
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_ENVIADA,
                'solicitante':  persona3,
                'operador':     None,
                'descripcion':  datos_f43(
                    persona3, 'camaguey', 'rad',
                    'Router WiFi doméstico',
                    'TP-Link', 'Archer AX55', 1, 'empleo_directo', 'definitiva',
                    rad='RAD-2025-001234'
                ),
                'obs_operador': '',
                'fecha_res':    False,
            },
            # 7. Aprobada temporal — Sony WH-1000XM5
            {
                'flujo':        Solicitud.FLUJO_F43,
                'estado':       Solicitud.ESTADO_APROBADA,
                'solicitante':  persona1,
                'operador':     operador2,
                'descripcion':  datos_f43(
                    persona1, 'la_habana', 'equipaje',
                    'Audífonos inalámbricos profesionales',
                    'Sony', 'WH-1000XM5', 1, 'muestra_expositiva', 'temporal',
                    vuelo='CU630', fecha_arribo='2025-05-20', pais='Colombia',
                    meses='3'
                ),
                'obs_operador': 'Muestra expositiva. Importación temporal de 3 meses aprobada.',
                'fecha_res':    True,
            },
            # 8. Enviada — equipo no listado (para cola del especialista)
            {
                'flujo':            Solicitud.FLUJO_F43,
                'estado':           Solicitud.ESTADO_EN_REVISION,
                'solicitante':      persona2,
                'operador':         operador1,
                'equipo_no_listado': True,
                'marca_manual':     'DJI',
                'modelo_manual':    'Mini 4 Pro',
                'descripcion':  datos_f43(
                    persona2, 'pinar_del_rio', 'equipaje',
                    'Dron de fotografía aérea con control remoto inalámbrico',
                    'DJI', 'Mini 4 Pro', 1, 'otros', 'definitiva',
                    vuelo='CU740', fecha_arribo='2025-07-05', pais='México'
                ),
                'obs_operador': 'Equipo no listado en catálogo. Derivado a especialista técnico.',
                'fecha_res':    False,
            },
        ]

        solicitudes_creadas = []

        for i, datos in enumerate(solicitudes_datos, 1):
            if Solicitud.objects.filter(
                solicitante = datos['solicitante'],
                equipo_descripcion__contains = datos['descripcion'][:50]
            ).exists():
                self.stdout.write(
                    f'  {self.style.WARNING("~")} Solicitud #{i} ya existe, omitiendo.'
                )
                continue

            solicitud = Solicitud(
                flujo              = datos['flujo'],
                estado             = datos['estado'],
                solicitante        = datos['solicitante'],
                operador_asignado  = datos.get('operador'),
                equipo_descripcion = datos['descripcion'],
                observaciones_operador = datos.get('obs_operador', ''),
                equipo_no_listado  = datos.get('equipo_no_listado', False),
                equipo_marca_manual  = datos.get('marca_manual', ''),
                equipo_modelo_manual = datos.get('modelo_manual', ''),
            )

            if datos.get('fecha_res'):
                solicitud.fecha_resolucion = timezone.now()

            solicitud.save()

            # Crear historial
            HistorialSolicitud.objects.create(
                solicitud       = solicitud,
                estado_anterior = '',
                estado_nuevo    = Solicitud.ESTADO_ENVIADA,
                usuario         = datos['solicitante'],
                observacion     = 'Solicitud creada y enviada por el solicitante.',
            )

            if datos['estado'] != Solicitud.ESTADO_ENVIADA and datos.get('operador'):
                HistorialSolicitud.objects.create(
                    solicitud       = solicitud,
                    estado_anterior = Solicitud.ESTADO_ENVIADA,
                    estado_nuevo    = datos['estado'],
                    usuario         = datos['operador'],
                    observacion     = datos.get('obs_operador', ''),
                )

            # Notificar a operadores de las solicitudes enviadas
            if datos['estado'] == Solicitud.ESTADO_ENVIADA:
                notificar_solicitud_nueva(solicitud)

            solicitudes_creadas.append(solicitud)
            self.stdout.write(
                f'  {self.style.SUCCESS("+")} {solicitud.numero} — '
                f'{solicitud.get_estado_display()} — '
                f'{solicitud.solicitante.get_nombre_completo()}'
            )

        return solicitudes_creadas

    # ─── Licencias ────────────────────────────────────────────────────────────
    def _crear_licencias(self, solicitudes, usuarios):

        self.stdout.write('\nGenerando licencias para solicitudes aprobadas...')

        operador = usuarios.get('operador1')

        for solicitud in solicitudes:
            if solicitud.estado == 'aprobada':
                try:
                    licencia = generar_licencia(solicitud, operador)
                    self.stdout.write(
                        f'  {self.style.SUCCESS("+")} {licencia.numero} — '
                        f'{solicitud.solicitante.get_nombre_completo()} — '
                        f'{"Temporal" if licencia.es_temporal else "Definitiva"}'
                    )
                except Exception as e:
                    self.stdout.write(
                        f'  {self.style.WARNING("~")} Ya existe licencia para {solicitud.numero}'
                    )