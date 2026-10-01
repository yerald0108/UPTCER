from django.test import TestCase, Client
from django.urls import reverse
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
# Modelo Usuario
# ═══════════════════════════════════════════════════════════════════════════════
class UsuarioModelTest(TestCase):

    def test_get_nombre_completo(self):
        """Verifica que get_nombre_completo retorna nombre + apellidos."""
        u = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'u1')
        self.assertEqual(u.get_nombre_completo(), 'Test Usuario')

    def test_str_usuario(self):
        """Verifica el __str__ del modelo."""
        u = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'u2')
        self.assertIn('u2', str(u))

    def test_username_unico(self):
        """No se pueden crear dos usuarios con el mismo username."""
        crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'mismo')
        with self.assertRaises(Exception):
            crear_usuario(Usuario.ROL_DIRECTIVO, 'mismo')

    def test_email_unico(self):
        """No se pueden crear dos usuarios con el mismo email."""
        Usuario.objects.create_user(
            username='u_email1', email='repetido@uptcer.cu',
            nombre='A', apellidos='B', rol=Usuario.ROL_PERSONA_NATURAL,
            password='test1234'
        )
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                username='u_email2', email='repetido@uptcer.cu',
                nombre='C', apellidos='D', rol=Usuario.ROL_DIRECTIVO,
                password='test1234'
            )

    def test_usuario_activo_por_defecto(self):
        """Un usuario nuevo debe estar activo por defecto."""
        u = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'u_activo')
        self.assertTrue(u.is_active)

    def test_usuario_no_es_staff_por_defecto(self):
        """Un usuario nuevo no debe ser staff por defecto."""
        u = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'u_staff')
        self.assertFalse(u.is_staff)

    def test_propiedades_rol_persona_natural(self):
        """Verifica propiedades de rol para persona natural."""
        u = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'u_pn')
        self.assertTrue(u.es_persona_natural)
        self.assertFalse(u.es_directivo)
        self.assertFalse(u.es_especialista)

    def test_propiedades_rol_especialista_movil(self):
        """Verifica propiedades de rol para especialista móvil."""
        u = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'u_esp_movil')
        self.assertTrue(u.es_especialista)
        self.assertTrue(u.es_especialista_base)
        self.assertFalse(u.es_especialista_superior)
        self.assertFalse(u.es_persona_natural)

    def test_propiedades_rol_especialista_superior(self):
        """Verifica propiedades de rol para especialista superior."""
        u = crear_usuario(Usuario.ROL_ESPECIALISTA_SUPERIOR, 'u_sup')
        self.assertTrue(u.es_especialista)
        self.assertTrue(u.es_especialista_superior)
        self.assertFalse(u.es_especialista_base)

    def test_propiedades_rol_directivo(self):
        """Verifica propiedades de rol para directivo."""
        u = crear_usuario(Usuario.ROL_DIRECTIVO, 'u_dir')
        self.assertTrue(u.es_directivo)
        self.assertFalse(u.es_persona_natural)
        self.assertFalse(u.es_especialista)

    def test_propiedades_rol_aduana(self):
        """Verifica propiedades de rol para aduana."""
        u = crear_usuario(Usuario.ROL_ADUANA, 'u_aduana')
        self.assertTrue(u.es_aduana)
        self.assertFalse(u.es_directivo)

    def test_es_operador_siempre_false(self):
        """es_operador siempre retorna False — rol eliminado."""
        u = crear_usuario(Usuario.ROL_DIRECTIVO, 'u_op_false')
        self.assertFalse(u.es_operador)

    def test_todos_los_roles_especialista_base(self):
        """Los 4 especialistas de área son es_especialista_base=True."""
        roles = [
            Usuario.ROL_ESPECIALISTA_RADIOFARO,
            Usuario.ROL_ESPECIALISTA_MOVIL,
            Usuario.ROL_ESPECIALISTA_MARITIMO,
            Usuario.ROL_ESPECIALISTA_INTERNET,
        ]
        for i, rol in enumerate(roles):
            u = crear_usuario(rol, f'u_esp_{i}')
            self.assertTrue(u.es_especialista_base, f'Fallo para rol {rol}')
            self.assertTrue(u.es_especialista, f'Fallo es_especialista para {rol}')


# ═══════════════════════════════════════════════════════════════════════════════
# Login / Logout
# ═══════════════════════════════════════════════════════════════════════════════
class LoginViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url_login = reverse('accounts:login')
        self.usuario = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'login_user')

    def test_login_get_muestra_formulario(self):
        """GET al login debe retornar 200."""
        r = self.client.get(self.url_login)
        self.assertEqual(r.status_code, 200)

    def test_login_correcto_redirige_dashboard(self):
        """Login con credenciales correctas redirige al dashboard."""
        r = self.client.post(self.url_login, {
            'username': 'login_user', 'password': 'test1234'
        })
        self.assertRedirects(r, reverse('accounts:dashboard'))

    def test_login_incorrecto_no_redirige(self):
        """Login con credenciales incorrectas no redirige."""
        r = self.client.post(self.url_login, {
            'username': 'login_user', 'password': 'mal'
        })
        self.assertEqual(r.status_code, 200)

    def test_login_campos_vacios(self):
        """Login con campos vacíos no redirige."""
        r = self.client.post(self.url_login, {'username': '', 'password': ''})
        self.assertEqual(r.status_code, 200)

    def test_login_usuario_inexistente(self):
        """Login con usuario inexistente no redirige."""
        r = self.client.post(self.url_login, {
            'username': 'noexiste', 'password': 'test1234'
        })
        self.assertEqual(r.status_code, 200)

    def test_logout_redirige_login(self):
        """Logout redirige al login."""
        self.client.login(username='login_user', password='test1234')
        r = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(r, self.url_login)

    def test_logout_solo_post(self):
        """Logout por GET no debe funcionar."""
        self.client.login(username='login_user', password='test1234')
        r = self.client.get(reverse('accounts:logout'))
        self.assertEqual(r.status_code, 405)

    def test_usuario_autenticado_redirige_desde_login(self):
        """Un usuario ya autenticado que va al login debe redirigir al dashboard."""
        self.client.login(username='login_user', password='test1234')
        r = self.client.get(self.url_login)
        self.assertRedirects(r, reverse('accounts:dashboard'))


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboards por rol
# ═══════════════════════════════════════════════════════════════════════════════
class DashboardViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:dashboard')

    def test_dashboard_sin_autenticar_redirige_login(self):
        """Sin autenticación el dashboard redirige al login."""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_dashboard_persona_natural(self):
        """Persona natural ve su dashboard."""
        u = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'd_pn')
        self.client.login(username='d_pn', password='test1234')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'accounts/dashboard_persona_natural.html')

    def test_dashboard_especialista_base(self):
        """Especialista de área ve su dashboard."""
        u = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'd_esp')
        self.client.login(username='d_esp', password='test1234')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'accounts/dashboard_especialista.html')

    def test_dashboard_especialista_superior(self):
        """Especialista superior ve su dashboard."""
        u = crear_usuario(Usuario.ROL_ESPECIALISTA_SUPERIOR, 'd_sup')
        self.client.login(username='d_sup', password='test1234')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'accounts/dashboard_especialista_superior.html')

    def test_dashboard_directivo(self):
        """Directivo ve su dashboard."""
        u = crear_usuario(Usuario.ROL_DIRECTIVO, 'd_dir')
        self.client.login(username='d_dir', password='test1234')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'accounts/dashboard_directivo.html')

    def test_dashboard_aduana(self):
        """Aduana ve su dashboard."""
        u = crear_usuario(Usuario.ROL_ADUANA, 'd_aduana')
        self.client.login(username='d_aduana', password='test1234')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'accounts/dashboard_aduana.html')


# ═══════════════════════════════════════════════════════════════════════════════
# Gestión de usuarios
# ═══════════════════════════════════════════════════════════════════════════════
class GestionUsuariosTest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.directivo = crear_usuario(Usuario.ROL_DIRECTIVO, 'g_dir')
        self.persona   = crear_usuario(Usuario.ROL_PERSONA_NATURAL, 'g_pn')
        self.esp       = crear_usuario(Usuario.ROL_ESPECIALISTA_MOVIL, 'g_esp')

    def test_lista_usuarios_solo_directivo(self):
        """Solo el directivo puede ver la lista de usuarios."""
        self.client.login(username='g_dir', password='test1234')
        r = self.client.get(reverse('accounts:lista_usuarios'))
        self.assertEqual(r.status_code, 200)

    def test_lista_usuarios_denegado_para_persona_natural(self):
        """Persona natural no puede ver la lista de usuarios."""
        self.client.login(username='g_pn', password='test1234')
        r = self.client.get(reverse('accounts:lista_usuarios'))
        self.assertEqual(r.status_code, 302)

    def test_lista_usuarios_denegado_para_especialista(self):
        """Especialista no puede ver la lista de usuarios."""
        self.client.login(username='g_esp', password='test1234')
        r = self.client.get(reverse('accounts:lista_usuarios'))
        self.assertEqual(r.status_code, 302)

    def test_crear_usuario_solo_directivo(self):
        """Solo el directivo puede crear usuarios."""
        self.client.login(username='g_dir', password='test1234')
        r = self.client.get(reverse('accounts:nuevo_usuario'))
        self.assertEqual(r.status_code, 200)

    def test_crear_usuario_denegado_para_especialista(self):
        """El especialista no puede crear usuarios."""
        self.client.login(username='g_esp', password='test1234')
        r = self.client.get(reverse('accounts:nuevo_usuario'))
        self.assertEqual(r.status_code, 302)

    def test_crear_usuario_post_exitoso(self):
        """El directivo puede crear un usuario nuevo correctamente."""
        self.client.login(username='g_dir', password='test1234')
        r = self.client.post(reverse('accounts:nuevo_usuario'), {
            'username':  'nuevo_esp',
            'email':     'nuevo@uptcer.cu',
            'nombre':    'Nuevo',
            'apellidos': 'Especialista',
            'rol':       Usuario.ROL_ESPECIALISTA_INTERNET,
            'password1': 'clave1234',
            'password2': 'clave1234',
        })
        self.assertTrue(Usuario.objects.filter(username='nuevo_esp').exists())

    def test_perfil_accesible_para_cualquier_usuario(self):
        """Cualquier usuario autenticado puede ver su perfil."""
        for username in ['g_dir', 'g_pn', 'g_esp']:
            self.client.login(username=username, password='test1234')
            r = self.client.get(reverse('accounts:perfil'))
            self.assertEqual(r.status_code, 200)

    def test_toggle_usuario_desactiva_otro_usuario(self):
        """El directivo puede desactivar a otro usuario."""
        self.client.login(username='g_dir', password='test1234')
        self.client.post(reverse('accounts:toggle_usuario', args=[self.persona.pk]))
        self.persona.refresh_from_db()
        self.assertFalse(self.persona.is_active)

    def test_toggle_usuario_no_puede_desactivarse_a_si_mismo(self):
        """El directivo no puede desactivar su propia cuenta."""
        self.client.login(username='g_dir', password='test1234')
        self.client.post(reverse('accounts:toggle_usuario', args=[self.directivo.pk]))
        self.directivo.refresh_from_db()
        self.assertTrue(self.directivo.is_active)