from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', Usuario.ROL_OPERADOR)
        return self.create_user(username, email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):

    # ─── Roles del sistema ────────────────────────────────────────────────────
    ROL_PERSONA_NATURAL      = 'persona_natural'
    ROL_ESPECIALISTA_RADIOFARO = 'especialista_radiofaro'
    ROL_ESPECIALISTA_MOVIL     = 'especialista_movil'
    ROL_ESPECIALISTA_MARITIMO  = 'especialista_maritimo'
    ROL_ESPECIALISTA_INTERNET  = 'especialista_internet'
    ROL_ESPECIALISTA_SUPERIOR  = 'especialista_superior'
    ROL_ADUANA               = 'aduana'
    ROL_DIRECTIVO            = 'directivo'

    ROLES = [
        (ROL_PERSONA_NATURAL,        'Persona Natural'),
        (ROL_ESPECIALISTA_RADIOFARO, 'Especialista Radiofaro'),
        (ROL_ESPECIALISTA_MOVIL,     'Especialista Móvil'),
        (ROL_ESPECIALISTA_MARITIMO,  'Especialista Marítimo'),
        (ROL_ESPECIALISTA_INTERNET,  'Especialista Internet'),
        (ROL_ESPECIALISTA_SUPERIOR,  'Especialista Superior'),
        (ROL_ADUANA,                 'Aduana'),
        (ROL_DIRECTIVO,              'Directivo'),
    ]

    # ─── Campos ───────────────────────────────────────────────────────────────
    username        = models.CharField('Usuario', max_length=150, unique=True)
    email           = models.EmailField('Correo electrónico', unique=True)
    nombre          = models.CharField('Nombre', max_length=100)
    apellidos       = models.CharField('Apellidos', max_length=100)
    rol             = models.CharField('Rol', max_length=30, choices=ROLES, default=ROL_PERSONA_NATURAL)
    telefono        = models.CharField('Teléfono', max_length=20, blank=True)
    activo          = models.BooleanField('Activo', default=True)
    fecha_registro  = models.DateTimeField('Fecha de registro', auto_now_add=True)

    # ─── Campos requeridos por Django ─────────────────────────────────────────
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['email', 'nombre', 'apellidos']

    class Meta:
        verbose_name        = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering            = ['apellidos', 'nombre']

    def __str__(self):
        return f'{self.nombre} {self.apellidos} ({self.get_rol_display()})'

    def get_nombre_completo(self):
        return f'{self.nombre} {self.apellidos}'

    # ─── Helpers de rol ───────────────────────────────────────────────────────────
    @property
    def es_persona_natural(self):
        return self.rol == self.ROL_PERSONA_NATURAL

    @property
    def es_especialista_radiofaro(self):
        return self.rol == self.ROL_ESPECIALISTA_RADIOFARO

    @property
    def es_especialista_movil(self):
        return self.rol == self.ROL_ESPECIALISTA_MOVIL

    @property
    def es_especialista_maritimo(self):
        return self.rol == self.ROL_ESPECIALISTA_MARITIMO

    @property
    def es_especialista_internet(self):
        return self.rol == self.ROL_ESPECIALISTA_INTERNET

    @property
    def es_especialista_superior(self):
        return self.rol == self.ROL_ESPECIALISTA_SUPERIOR

    @property
    def es_especialista_base(self):
        """True solo para los 4 especialistas de área (no el superior)."""
        return self.rol in [
            self.ROL_ESPECIALISTA_RADIOFARO,
            self.ROL_ESPECIALISTA_MOVIL,
            self.ROL_ESPECIALISTA_MARITIMO,
            self.ROL_ESPECIALISTA_INTERNET,
        ]

    @property
    def es_aduana(self):
        return self.rol == self.ROL_ADUANA

    @property
    def es_directivo(self):
        return self.rol == self.ROL_DIRECTIVO

    @property
    def es_operador(self):
        """Compatibilidad temporal — siempre False, el rol fue eliminado."""
        return False