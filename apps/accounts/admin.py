from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display  = ('username', 'nombre', 'apellidos', 'email', 'rol', 'is_active')
    list_filter   = ('rol', 'is_active')
    search_fields = ('username', 'nombre', 'apellidos', 'email')
    ordering      = ('apellidos', 'nombre')

    fieldsets = (
        ('Credenciales',  {'fields': ('username', 'password')}),
        ('Información personal', {'fields': ('nombre', 'apellidos', 'email', 'telefono')}),
        ('Rol y acceso',  {'fields': ('rol', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permisos',      {'fields': ('groups', 'user_permissions')}),
        ('Fechas',        {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'nombre', 'apellidos', 'rol', 'password1', 'password2'),
        }),
    )