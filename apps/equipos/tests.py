import json
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import Usuario
from apps.equipos.models import Equipo, CategoriaEquipo


def crear_usuario(rol, username=None, password='test1234'):
    username = username or f'user_{rol}'
    return Usuario.objects.create_user(
        username=username, email=f'{username}@uptcer.cu',
        nombre='Test', apellidos='Usuario', rol=rol, password=password,
    )


def crear_categoria(nombre='Teléfonos móviles'):
    cat, _ = CategoriaEquipo.objects.get_or_create(
        nombre=nombre, defaults={'descripcion': 'Descripción de prueba'}
    )
    return cat


def crear_equipo(categoria=None, marca='Samsung', modelo='Galaxy S24'):
    if categoria is None:
        categoria = crear_categoria()
    equipo, _ = Equipo.objects.get_or_create(
        marca=marca, modelo=modelo,
        defaults={
            'categoria': categoria,
            'nombre': f'{marca} {modelo}',
            'descripcion': 'Equipo de prueba',
            'banda_frecuencia': 'libre',
            'requiere_permiso': True,
            'activo': True,
        }
    )
    return equipo


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo CategoriaEquipo
# ═══════════════════════════════════════════════════════════════════════════════
class CategoriaEquipoModelTest(TestCase):

    def test_crear_categoria(self):
        """Se puede crear una categoría correctamente."""
        cat = CategoriaEquipo.objects.create(
            nombre='Routers', descripcion='Equipos de red'
        )
        self.assertIsNotNone(cat.pk)

    def test_str_categoria(self):
        """El __str__ retorna el nombre de la categoría."""
        cat = crear_categoria('Tablets')
        self.assertEqual(str(cat), 'Tablets')

    def test_nombre_unico(self):
        """No se pueden crear dos categorías con el mismo nombre."""
        CategoriaEquipo.objects.create(nombre='Única', descripcion='Test')
        with self.assertRaises(Exception):
            CategoriaEquipo.objects.create(nombre='Única', descripcion='Otra')


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo Equipo
# ═══════════════════════════════════════════════════════════════════════════════
class EquipoModelTest(TestCase):

    def setUp(self):
        self.categoria = crear_categoria()

    def test_crear_equipo(self):
        """Se puede crear un equipo correctamente."""
        e = Equipo.objects.create(
            categoria=self.categoria, nombre='Test', marca='Apple',
            modelo='iPhone 15', banda_frecuencia='libre',
            requiere_permiso=True, activo=True,
        )
        self.assertIsNotNone(e.pk)

    def test_str_equipo(self):
        """El __str__ incluye marca, modelo y nombre."""
        e = crear_equipo(self.categoria, 'Samsung', 'Galaxy S24')
        self.assertIn('Samsung', str(e))
        self.assertIn('Galaxy S24', str(e))

    def test_marca_modelo_unico(self):
        """No se pueden crear dos equipos con la misma marca y modelo."""
        Equipo.objects.create(
            categoria=self.categoria, nombre='A', marca='Sony',
            modelo='WH1000XM5', banda_frecuencia='libre',
            requiere_permiso=False, activo=True,
        )
        with self.assertRaises(Exception):
            Equipo.objects.create(
                categoria=self.categoria, nombre='B', marca='Sony',
                modelo='WH1000XM5', banda_frecuencia='libre',
                requiere_permiso=False, activo=True,
            )

    def test_activo_por_defecto(self):
        """Un equipo nuevo está activo por defecto."""
        e = crear_equipo(self.categoria, 'Xiaomi', 'Redmi Note 13')
        self.assertTrue(e.activo)

    def test_propiedad_es_banda_libre(self):
        """es_banda_libre es True solo para banda libre."""
        e = crear_equipo(self.categoria)
        self.assertTrue(e.es_banda_libre)

    def test_propiedad_es_restringido(self):
        """es_restringido es True solo para frecuencia restringida."""
        e = Equipo.objects.create(
            categoria=self.categoria, nombre='Radio', marca='Motorola',
            modelo='DP4400e', banda_frecuencia='restringida',
            requiere_permiso=True, activo=True,
        )
        self.assertTrue(e.es_restringido)

    def test_fecha_registro_automatica(self):
        """La fecha de registro se asigna automáticamente."""
        e = crear_equipo(self.categoria, 'TP-Link', 'Archer AX55')
        self.assertIsNotNone(e.fecha_registro)

    def test_fecha_actualizacion_automatica(self):
        """La fecha de actualización se asigna automáticamente."""
        e = crear_equipo(self.categoria, 'Cisco', 'RV340')
        self.assertIsNotNone(e.fecha_actualizacion)


# ═══════════════════════════════════════════════════════════════════════════════
# Vistas de equipos
# ═══════════════════════════════════════════════════════════════════════════════
class EquipoVistaTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'eq_pn')
        self.esp       = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'eq_esp')
        self.superior  = crear_usuario(Usuario.ROL_ESPECIALISTA_SUPERIOR, 'eq_sup')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'eq_dir')
        self.categoria = crear_categoria()
        self.equipo    = crear_equipo(self.categoria)

    def test_lista_equipos_sin_autenticar_redirige(self):
        """Sin autenticación redirige al login."""
        r = self.client.get(reverse('equipos:lista'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('acceso', r['Location'])

    def test_lista_equipos_accesible_autenticado(self):
        """Cualquier usuario autenticado puede ver el catálogo."""
        for username in ['eq_pn', 'eq_esp', 'eq_dir']:
            self.client.login(username=username, password='test1234')
            r = self.client.get(reverse('equipos:lista'))
            self.assertEqual(r.status_code, 200)

    def test_lista_equipos_muestra_equipos_activos(self):
        """La lista muestra solo equipos activos."""
        self.client.login(username='eq_esp', password='test1234')
        r = self.client.get(reverse('equipos:lista'))
        for e in r.context['equipos']:
            self.assertTrue(e.activo)

    def test_detalle_equipo_accesible(self):
        """El detalle de un equipo es accesible para cualquier usuario autenticado."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(reverse('equipos:detalle', args=[self.equipo.pk]))
        self.assertEqual(r.status_code, 200)

    def test_nuevo_equipo_accesible_para_especialista(self):
        """El especialista puede acceder al formulario de nuevo equipo."""
        self.client.login(username='eq_esp', password='test1234')
        r = self.client.get(reverse('equipos:nuevo'))
        self.assertEqual(r.status_code, 200)

    def test_nuevo_equipo_accesible_para_superior(self):
        """El especialista superior puede acceder al formulario de nuevo equipo."""
        self.client.login(username='eq_sup', password='test1234')
        r = self.client.get(reverse('equipos:nuevo'))
        self.assertEqual(r.status_code, 200)

    def test_nuevo_equipo_denegado_para_persona_natural(self):
        """Persona natural no puede acceder al formulario de nuevo equipo."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(reverse('equipos:nuevo'))
        self.assertEqual(r.status_code, 302)

    def test_crear_equipo_post_exitoso(self):
        """El directivo puede crear un equipo nuevo correctamente."""
        self.client.login(username='eq_dir', password='test1234')
        r = self.client.post(reverse('equipos:nuevo'), {
            'nombre': 'Laptop Lenovo',
            'marca': 'Lenovo',
            'modelo': 'ThinkPad X1',
            'categoria': self.categoria.pk,
            'descripcion': 'Laptop empresarial',
            'banda_frecuencia': 'libre',
            'requiere_permiso': True,
        })
        self.assertTrue(
            Equipo.objects.filter(marca='Lenovo', modelo='ThinkPad X1').exists()
        )

    def test_crear_equipo_marca_modelo_duplicado(self):
        """No se puede crear un equipo con marca y modelo ya existente."""
        self.client.login(username='eq_dir', password='test1234')
        self.client.post(reverse('equipos:nuevo'), {
            'nombre': 'Samsung Original',
            'marca': 'Samsung',
            'modelo': 'Galaxy S24',
            'categoria': self.categoria.pk,
            'descripcion': 'Duplicado',
            'banda_frecuencia': 'libre',
            'requiere_permiso': True,
        })
        self.assertEqual(
            Equipo.objects.filter(marca='Samsung', modelo='Galaxy S24').count(), 1
        )

    def test_desactivar_equipo(self):
        """El directivo puede desactivar un equipo."""
        self.client.login(username='eq_dir', password='test1234')
        self.client.post(reverse('equipos:desactivar', args=[self.equipo.pk]))
        self.equipo.refresh_from_db()
        self.assertFalse(self.equipo.activo)

    def test_desactivar_equipo_denegado_para_persona_natural(self):
        """Persona natural no puede desactivar equipos."""
        self.client.login(username='eq_pn', password='test1234')
        self.client.post(reverse('equipos:desactivar', args=[self.equipo.pk]))
        self.equipo.refresh_from_db()
        self.assertTrue(self.equipo.activo)

    def test_activar_equipo_desactivado(self):
        """El directivo puede reactivar un equipo desactivado."""
        self.equipo.activo = False
        self.equipo.save()
        self.client.login(username='eq_dir', password='test1234')
        self.client.post(reverse('equipos:desactivar', args=[self.equipo.pk]))
        self.equipo.refresh_from_db()
        self.assertTrue(self.equipo.activo)

    def test_busqueda_ajax_retorna_json(self):
        """El endpoint AJAX de búsqueda retorna JSON."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(
            reverse('equipos:buscar_ajax'), {'q': 'Samsung'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertIn('equipos', data)

    def test_busqueda_ajax_query_corta_retorna_vacio(self):
        """El endpoint AJAX no busca con 1 carácter."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(reverse('equipos:buscar_ajax'), {'q': 'S'})
        data = json.loads(r.content)
        self.assertEqual(data['equipos'], [])

    def test_busqueda_ajax_vacia_retorna_todos(self):
        """El endpoint AJAX con q vacío retorna todos los equipos."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(reverse('equipos:buscar_ajax'), {'q': ''})
        data = json.loads(r.content)
        self.assertGreater(len(data['equipos']), 0)

    def test_busqueda_por_marca(self):
        """La búsqueda filtra correctamente por marca."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(reverse('equipos:buscar_ajax'), {'q': 'Samsung'})
        data = json.loads(r.content)
        for e in data['equipos']:
            self.assertIn('Samsung', e['marca'])

    def test_busqueda_sin_resultados(self):
        """Una búsqueda sin resultados retorna lista vacía."""
        self.client.login(username='eq_pn', password='test1234')
        r = self.client.get(
            reverse('equipos:buscar_ajax'), {'q': 'MarcaQueNoExisteXYZ123'}
        )
        data = json.loads(r.content)
        self.assertEqual(data['equipos'], [])


# ═══════════════════════════════════════════════════════════════════════════════
# Vistas de categorías
# ═══════════════════════════════════════════════════════════════════════════════
class CategoriaVistaTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'cat_pn')
        self.esp       = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'cat_esp')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'cat_dir')

    def test_categorias_accesible_para_especialista(self):
        """El especialista puede acceder a la gestión de categorías."""
        self.client.login(username='cat_esp', password='test1234')
        r = self.client.get(reverse('equipos:categorias'))
        self.assertEqual(r.status_code, 200)

    def test_categorias_accesible_para_directivo(self):
        """El directivo puede acceder a la gestión de categorías."""
        self.client.login(username='cat_dir', password='test1234')
        r = self.client.get(reverse('equipos:categorias'))
        self.assertEqual(r.status_code, 200)

    def test_categorias_denegado_para_persona_natural(self):
        """Persona natural no puede acceder a la gestión de categorías."""
        self.client.login(username='cat_pn', password='test1234')
        r = self.client.get(reverse('equipos:categorias'))
        self.assertEqual(r.status_code, 302)

    def test_crear_categoria_post_exitoso(self):
        """El directivo puede crear una categoría nueva."""
        self.client.login(username='cat_dir', password='test1234')
        self.client.post(reverse('equipos:categorias'), {
            'nombre': 'Drones',
            'descripcion': 'Vehículos aéreos no tripulados',
        })
        self.assertTrue(
            CategoriaEquipo.objects.filter(nombre='Drones').exists()
        )