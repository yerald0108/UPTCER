from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Usuario


# ─── Factory de usuarios de prueba ───────────────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE MODELO — Usuario
# ═══════════════════════════════════════════════════════════════════════════════

class UsuarioModelTest(TestCase):

    def setUp(self):
        self.persona = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.operador = crear_usuario(Usuario.ROL_OPERADOR, 'operador')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA, 'especialista')
        self.aduana = crear_usuario(Usuario.ROL_ADUANA, 'aduana')
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'directivo')

    def test_propiedades_rol_persona_natural(self):
        """Verifica que las propiedades de rol son correctas para persona natural."""
        self.assertTrue(self.persona.es_persona_natural)
        self.assertFalse(self.persona.es_operador)
        self.assertFalse(self.persona.es_especialista)
        self.assertFalse(self.persona.es_aduana)
        self.assertFalse(self.persona.es_directivo)

    def test_propiedades_rol_operador(self):
        """Verifica que las propiedades de rol son correctas para operador."""
        self.assertTrue(self.operador.es_operador)
        self.assertFalse(self.operador.es_persona_natural)
        self.assertFalse(self.operador.es_especialista)

    def test_propiedades_rol_especialista(self):
        """Verifica que las propiedades de rol son correctas para especialista."""
        self.assertTrue(self.especialista.es_especialista)
        self.assertFalse(self.especialista.es_operador)

    def test_propiedades_rol_aduana(self):
        """Verifica que las propiedades de rol son correctas para aduana."""
        self.assertTrue(self.aduana.es_aduana)
        self.assertFalse(self.aduana.es_directivo)

    def test_propiedades_rol_directivo(self):
        """Verifica que las propiedades de rol son correctas para directivo."""
        self.assertTrue(self.directivo.es_directivo)
        self.assertFalse(self.directivo.es_persona_natural)

    def test_get_nombre_completo(self):
        """Verifica que get_nombre_completo retorna nombre + apellidos."""
        self.assertEqual(self.persona.get_nombre_completo(), 'Test Usuario')

    def test_str_usuario(self):
        """Verifica el __str__ del modelo."""
        self.assertIn('Test Usuario', str(self.persona))
        self.assertIn('Persona Natural', str(self.persona))

    def test_usuario_activo_por_defecto(self):
        """Un usuario nuevo debe estar activo por defecto."""
        self.assertTrue(self.persona.is_active)

    def test_usuario_no_es_staff_por_defecto(self):
        """Un usuario nuevo no debe ser staff por defecto."""
        self.assertFalse(self.persona.is_staff)

    def test_email_unico(self):
        """No se pueden crear dos usuarios con el mismo email."""
        campo_email = Usuario._meta.get_field('email')
        self.assertTrue(campo_email.unique)

    def test_username_unico(self):
        """No se pueden crear dos usuarios con el mismo username."""
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                username  = 'persona',  # mismo username que self.persona
                email     = 'nuevo@uptcer.cu',
                nombre    = 'Nuevo',
                apellidos = 'Usuario',
                password  = 'test1234',
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Login / Logout
# ═══════════════════════════════════════════════════════════════════════════════

class LoginViewTest(TestCase):

    def setUp(self):
        self.client  = Client()
        self.persona = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'persona')
        self.url_login = reverse('accounts:login')

    def test_login_get_muestra_formulario(self):
        """GET al login debe retornar 200."""
        response = self.client.get(self.url_login)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_correcto_redirige_dashboard(self):
        """Login con credenciales correctas redirige al dashboard."""
        response = self.client.post(self.url_login, {
            'username': 'persona',
            'password': 'test1234',
        })
        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_login_incorrecto_no_redirige(self):
        """Login con credenciales incorrectas no redirige."""
        response = self.client.post(self.url_login, {
            'username': 'persona',
            'password': 'contraseña_incorrecta',
        })
        self.assertEqual(response.status_code, 200)

    def test_login_usuario_inexistente(self):
        """Login con usuario inexistente no redirige."""
        response = self.client.post(self.url_login, {
            'username': 'no_existe',
            'password': 'test1234',
        })
        self.assertEqual(response.status_code, 200)

    def test_login_campos_vacios(self):
        """Login con campos vacíos no redirige."""
        response = self.client.post(self.url_login, {
            'username': '',
            'password': '',
        })
        self.assertEqual(response.status_code, 200)

    def test_usuario_autenticado_redirige_desde_login(self):
        """Un usuario ya autenticado que va al login debe redirigir al dashboard."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(self.url_login)
        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_logout_redirige_login(self):
        """Logout redirige al login."""
        self.client.login(username='persona', password='test1234')
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)

    def test_logout_solo_post(self):
        """Logout por GET no debe funcionar."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 405)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Dashboard por rol
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardViewTest(TestCase):

    def setUp(self):
        self.client       = Client()
        self.persona      = crear_usuario(Usuario.ROL_PERSONA_NATURAL,  'persona')
        self.operador     = crear_usuario(Usuario.ROL_OPERADOR,         'operador')
        self.especialista = crear_usuario(Usuario.ROL_ESPECIALISTA,     'especialista')
        self.aduana       = crear_usuario(Usuario.ROL_ADUANA,           'aduana')
        self.directivo    = crear_usuario(Usuario.ROL_DIRECTIVO,        'directivo')
        self.url = reverse('accounts:dashboard')

    def test_dashboard_sin_autenticar_redirige_login(self):
        """Sin autenticación el dashboard redirige al login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('acceso', response.url)

    def test_dashboard_persona_natural(self):
        """Persona natural ve su dashboard correcto."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard_persona_natural.html')

    def test_dashboard_operador(self):
        """Operador ve su dashboard correcto."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard_operador.html')

    def test_dashboard_especialista(self):
        """Especialista ve su dashboard correcto."""
        self.client.login(username='especialista', password='test1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard_especialista.html')

    def test_dashboard_aduana(self):
        """Aduana ve su dashboard correcto."""
        self.client.login(username='aduana', password='test1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard_aduana.html')

    def test_dashboard_directivo(self):
        """Directivo ve su dashboard correcto."""
        self.client.login(username='directivo', password='test1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard_directivo.html')


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VISTAS — Gestión de usuarios
# ═══════════════════════════════════════════════════════════════════════════════

class GestionUsuariosTest(TestCase):

    def setUp(self):
        self.client    = Client()
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO,        'directivo')
        self.operador  = crear_usuario(Usuario.ROL_OPERADOR,         'operador')
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL,  'persona')

    def test_lista_usuarios_solo_directivo_y_operador(self):
        """Solo directivo y operador pueden ver la lista de usuarios."""
        self.client.login(username='directivo', password='test1234')
        response = self.client.get(reverse('accounts:lista_usuarios'))
        self.assertEqual(response.status_code, 200)

        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('accounts:lista_usuarios'))
        self.assertEqual(response.status_code, 200)

    def test_lista_usuarios_denegado_para_persona_natural(self):
        """Persona natural no puede ver la lista de usuarios."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('accounts:lista_usuarios'))
        self.assertEqual(response.status_code, 302)

    def test_crear_usuario_solo_directivo(self):
        """Solo el directivo puede crear usuarios."""
        self.client.login(username='directivo', password='test1234')
        response = self.client.get(reverse('accounts:nuevo_usuario'))
        self.assertEqual(response.status_code, 200)

    def test_crear_usuario_denegado_para_operador(self):
        """El operador no puede crear usuarios."""
        self.client.login(username='operador', password='test1234')
        response = self.client.get(reverse('accounts:nuevo_usuario'))
        self.assertEqual(response.status_code, 302)

    def test_crear_usuario_post_exitoso(self):
        """El directivo puede crear un usuario nuevo correctamente."""
        self.client.login(username='directivo', password='test1234')
        response = self.client.post(reverse('accounts:nuevo_usuario'), {
            'username':  'nuevo_usuario',
            'email':     'nuevo@uptcer.cu',
            'nombre':    'Nuevo',
            'apellidos': 'Usuario',
            'rol':       Usuario.ROL_OPERADOR,
            'password1': 'clave123',
            'password2': 'clave123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(username='nuevo_usuario').exists())

    def test_toggle_usuario_no_puede_desactivarse_a_si_mismo(self):
        """El directivo no puede desactivar su propia cuenta."""
        self.client.login(username='directivo', password='test1234')
        response = self.client.post(
            reverse('accounts:toggle_usuario', args=[self.directivo.pk])
        )
        self.directivo.refresh_from_db()
        self.assertTrue(self.directivo.is_active)

    def test_toggle_usuario_desactiva_otro_usuario(self):
        """El directivo puede desactivar a otro usuario."""
        self.client.login(username='directivo', password='test1234')
        self.client.post(
            reverse('accounts:toggle_usuario', args=[self.operador.pk])
        )
        self.operador.refresh_from_db()
        self.assertFalse(self.operador.is_active)

    def test_perfil_accesible_para_cualquier_usuario(self):
        """Cualquier usuario autenticado puede ver su perfil."""
        self.client.login(username='persona', password='test1234')
        response = self.client.get(reverse('accounts:perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/perfil.html')