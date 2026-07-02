from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import Usuario
from apps.equipos.models import CategoriaEquipo, Equipo


# ─── Factory ─────────────────────────────────────────────────────────────────
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


def crear_categoria(nombre='Teléfonos móviles'):
    return CategoriaEquipo.objects.create(
        nombre      = nombre,
        descripcion = 'Categoría de prueba',
    )


def crear_equipo(categoria=None, banda='libre'):
    if not categoria:
        categoria = crear_categoria()
    return Equipo.objects.create(
        categoria        = categoria,
        nombre           = 'Teléfono inteligente',
        marca            = 'Samsung',
        modelo           = 'Galaxy S24',
        descripcion      = 'Equipo de prueba',
        banda_frecuencia = banda,
        requiere_permiso = True,
        activo           = True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — CategoriaEquipo
# ═══════════════════════════════════════════════════════════════════════════════

class CategoriaEquipoModelTest(TestCase):

    def test_crear_categoria(self):
        """Se puede crear una categoría correctamente."""
        cat = crear_categoria('Routers')
        self.assertEqual(cat.nombre, 'Routers')
        self.assertIsNotNone(cat.pk)

    def test_str_categoria(self):
        """El __str__ retorna el nombre de la categoría."""
        cat = crear_categoria('Tablets')
        self.assertEqual(str(cat), 'Tablets')

    def test_nombre_unico(self):
        """No se pueden crear dos categorías con el mismo nombre."""
        crear_categoria('Routers')
        with self.assertRaises(Exception):
            crear_categoria('Routers')


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — Equipo
# ═══════════════════════════════════════════════════════════════════════════════

class EquipoModelTest(TestCase):

    def setUp(self):
        self.categoria = crear_categoria()

    def test_crear_equipo(self):
        """Se puede crear un equipo correctamente."""
        equipo = crear_equipo(self.categoria)
        self.assertEqual(equipo.marca, 'Samsung')
        self.assertEqual(equipo.modelo, 'Galaxy S24')
        self.assertTrue(equipo.activo)

    def test_str_equipo(self):
        """El __str__ incluye marca, modelo y nombre."""
        equipo = crear_equipo(self.categoria)
        self.assertIn('Samsung', str(equipo))
        self.assertIn('Galaxy S24', str(equipo))

    def test_propiedad_es_banda_libre(self):
        """es_banda_libre es True solo para banda libre."""
        eq_libre      = crear_equipo(self.categoria, banda='libre')
        eq_restringida = Equipo.objects.create(
            categoria=self.categoria, nombre='Router', marca='Cisco',
            modelo='RV340', banda_frecuencia='restringida',
            requiere_permiso=True, activo=True,
        )
        self.assertTrue(eq_libre.es_banda_libre)
        self.assertFalse(eq_restringida.es_banda_libre)

    def test_propiedad_es_restringido(self):
        """es_restringido es True solo para frecuencia restringida."""
        eq_restringida = Equipo.objects.create(
            categoria=self.categoria, nombre='Router', marca='Cisco',
            modelo='RV340', banda_frecuencia='restringida',
            requiere_permiso=True, activo=True,
        )
        eq_libre = crear_equipo(self.categoria, banda='libre')
        self.assertTrue(eq_restringida.es_restringido)
        self.assertFalse(eq_libre.es_restringido)

    def test_marca_modelo_unico(self):
        """No se pueden crear dos equipos con la misma marca y modelo."""
        crear_equipo(self.categoria)
        with self.assertRaises(Exception):
            Equipo.objects.create(
                categoria        = self.categoria,
                nombre           = 'Otro nombre',
                marca            = 'Samsung',
                modelo           = 'Galaxy S24',
                banda_frecuencia = 'libre',
                requiere_permiso = True,
                activo           = True,
            )

    def test_activo_por_defecto(self):
        """Un equipo nuevo está activo por defecto."""
        equipo = crear_equipo(self.categoria)
        self.assertTrue(equipo.activo)

    def test_fecha_registro_automatica(self):
        """La fecha de registro se asigna automáticamente."""
        equipo = crear_equipo(self.categoria)
        self.assertIsNotNone(equipo.fecha_registro)

    def test_fecha_actualizacion_automatica(self):
        """La fecha de actualización se asigna automáticamente."""
        equipo = crear_equipo(self.categoria)
        self.assertIsNotNone(equipo.fecha_actualizacion)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Catálogo de equipos
# ═══════════════════════════════════════════════════════════════════════════════

class EquipoVistaTest(TestCase):

    def setUp(self):
        self.client       = Client()
        self.persona      = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador     = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA,    'especialista')
        self.directivo    = crear_usuario(Usuario.ROL_DIRECTIVO,       'directivo')
        self.categoria    = crear_categoria()
        self.equipo       = crear_equipo(self.categoria)

    def test_lista_equipos_accesible_autenticado(self):
        """Cualquier usuario autenticado puede ver el catálogo."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('equipos:lista'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'equipos/lista.html')

    def test_lista_equipos_sin_autenticar_redirige(self):
        """Sin autenticación redirige al login."""
        response = self.client.get(reverse('equipos:lista'))
        self.assertEqual(response.status_code, 302)

    def test_lista_equipos_muestra_equipos_activos(self):
        """La lista muestra solo equipos activos."""
        equipo_inactivo = Equipo.objects.create(
            categoria=self.categoria, nombre='Inactivo', marca='LG',
            modelo='X100', banda_frecuencia='libre',
            requiere_permiso=True, activo=False,
        )
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('equipos:lista'))
        equipos = list(response.context['equipos'])
        self.assertIn(self.equipo, equipos)
        self.assertNotIn(equipo_inactivo, equipos)

    def test_busqueda_por_marca(self):
        """La búsqueda filtra correctamente por marca."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('equipos:lista'), {'q': 'Samsung'})
        equipos = list(response.context['equipos'])
        self.assertIn(self.equipo, equipos)

    def test_busqueda_sin_resultados(self):
        """Una búsqueda sin resultados retorna lista vacía."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('equipos:lista'), {'q': 'marcaquenoexiste'})
        equipos = list(response.context['equipos'])
        self.assertEqual(len(equipos), 0)

    def test_detalle_equipo_accesible(self):
        """El detalle de un equipo es accesible para cualquier usuario autenticado."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('equipos:detalle', args=[self.equipo.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'equipos/detalle.html')

    def test_nuevo_equipo_accesible_para_operador(self):
        """El operador puede acceder al formulario de nuevo equipo."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('equipos:nuevo'))
        self.assertEqual(response.status_code, 200)

    def test_nuevo_equipo_denegado_para_persona_natural(self):
        """Persona natural no puede acceder al formulario de nuevo equipo."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('equipos:nuevo'))
        self.assertEqual(response.status_code, 302)

    def test_crear_equipo_post_exitoso(self):
        """El operador puede crear un equipo nuevo correctamente."""
        self.client.login(username='operador', password='test1234')
        response = self.client.post(reverse('equipos:nuevo'), {
            'categoria':        self.categoria.pk,
            'nombre':           'Nuevo equipo de prueba',
            'marca':            'Apple',
            'modelo':           'iPhone 15',
            'descripcion':      'Teléfono Apple',
            'banda_frecuencia': 'libre',
            'requiere_permiso': True,
            'activo':           True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Equipo.objects.filter(marca='Apple', modelo='iPhone 15').exists())

    def test_crear_equipo_marca_modelo_duplicado(self):
        """No se puede crear un equipo con marca y modelo ya existente."""
        self.client.login(username='operador', password='test1234')
        response = self.client.post(reverse('equipos:nuevo'), {
            'categoria':        self.categoria.pk,
            'nombre':           'Duplicado',
            'marca':            'Samsung',
            'modelo':           'Galaxy S24',
            'banda_frecuencia': 'libre',
            'requiere_permiso': True,
            'activo':           True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Equipo.objects.filter(marca='Samsung', modelo='Galaxy S24').count(), 1)

    def test_desactivar_equipo(self):
        """El operador puede desactivar un equipo."""
        self.client.login(username='operador', password='test1234')
        self.client.post(reverse('equipos:desactivar', args=[self.equipo.pk]))
        self.equipo.refresh_from_db()
        self.assertFalse(self.equipo.activo)

    def test_activar_equipo_desactivado(self):
        """El operador puede reactivar un equipo desactivado."""
        self.equipo.activo = False
        self.equipo.save()
        self.client.login(username='operador', password='test1234')
        self.client.post(reverse('equipos:desactivar', args=[self.equipo.pk]))
        self.equipo.refresh_from_db()
        self.assertTrue(self.equipo.activo)

    def test_desactivar_equipo_denegado_para_persona_natural(self):
        """Persona natural no puede desactivar equipos."""
        self.client.login(username='persona', password='test1234')
        self.client.post(reverse('equipos:desactivar', args=[self.equipo.pk]))
        self.equipo.refresh_from_db()
        self.assertTrue(self.equipo.activo)

    def test_busqueda_ajax_retorna_json(self):
        """El endpoint AJAX de búsqueda retorna JSON."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(
            reverse('equipos:buscar_ajax'),
            {'q': 'Samsung'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertIn('equipos', data)
        self.assertEqual(len(data['equipos']), 1)
        self.assertEqual(data['equipos'][0]['marca'], 'Samsung')

    def test_busqueda_ajax_query_corta_retorna_vacio(self):
        """El endpoint AJAX no busca con menos de 2 caracteres."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(
            reverse('equipos:buscar_ajax'),
            {'q': 'S'},
        )
        import json
        data = json.loads(response.content)
        self.assertEqual(data['equipos'], [])


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Categorías
# ═══════════════════════════════════════════════════════════════════════════════

class CategoriaVistaTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.operador = crear_usuario(Usuario.ROL_OPERADOR,        'operador')
        self.persona  = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')

    def test_categorias_accesible_para_operador(self):
        """El operador puede acceder a la gestión de categorías."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('equipos:categorias'))
        self.assertEqual(response.status_code, 200)

    def test_categorias_denegado_para_persona_natural(self):
        """Persona natural no puede acceder a la gestión de categorías."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('equipos:categorias'))
        self.assertEqual(response.status_code, 302)

    def test_crear_categoria_post_exitoso(self):
        """El operador puede crear una categoría nueva."""
        self.client.login(username='operador', password='test1234')
        response = self.client.post(reverse('equipos:categorias'), {
            'nombre':      'Laptops',
            'descripcion': 'Computadoras portátiles',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CategoriaEquipo.objects.filter(nombre='Laptops').exists())