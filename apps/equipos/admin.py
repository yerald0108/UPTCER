from django.contrib import admin
from .models import CategoriaEquipo, Equipo


@admin.register(CategoriaEquipo)
class CategoriaEquipoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'descripcion')
    search_fields = ('nombre',)
    ordering      = ('nombre',)


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display   = ('nombre', 'marca', 'modelo', 'categoria', 'banda_frecuencia', 'requiere_permiso', 'activo')
    list_filter    = ('categoria', 'banda_frecuencia', 'requiere_permiso', 'activo')
    search_fields  = ('nombre', 'marca', 'modelo')
    ordering       = ('nombre',)
    list_editable  = ('activo',)