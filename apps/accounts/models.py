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
    ROL_PERSONA_NATURAL  = 'persona_natural'
    ROL_OPERADOR         = 'operador'
    ROL_ESPECIALISTA     = 'especialista'
    ROL_ADUANA           = 'aduana'
    ROL_DIRECTIVO        = 'directivo'

    ROLES = [
        (ROL_PERSONA_NATURAL, 'Persona Natural'),
        (ROL_OPERADOR,        'Operador'),
        (ROL_ESPECIALISTA,    'Especialista Técnico'),
        (ROL_ADUANA,          'Aduana'),
        (ROL_DIRECTIVO,       'Directivo'),
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

    # ─── Helpers de rol ───────────────────────────────────────────────────────
    @property
    def es_persona_natural(self):
        return self.rol == self.ROL_PERSONA_NATURAL

    @property
    def es_operador(self):
        return self.rol == self.ROL_OPERADOR

    @property
    def es_especialista(self):
        return self.rol == self.ROL_ESPECIALISTA

    @property
    def es_aduana(self):
        return self.rol == self.ROL_ADUANA

    @property
    def es_directivo(self):
        return self.rol == self.ROL_DIRECTIVO