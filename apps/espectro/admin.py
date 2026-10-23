from django.contrib import admin
from .models import FactorFrecuencia, FactorServicio, FactorK, IntensidadCampoE

@admin.register(FactorFrecuencia)
class FactorFrecuenciaAdmin(admin.ModelAdmin):
    list_display = ('banda_min', 'banda_max', 'valor', 'descripcion')
    search_fields = ('descripcion',)

@admin.register(FactorServicio)
class FactorServicioAdmin(admin.ModelAdmin):
    list_display = ('grupo', 'categoria', 'subcategoria', 'valor_c', 'activo')
    list_filter = ('grupo', 'activo', 'categoria')
    search_fields = ('subcategoria', 'categoria')
    ordering = ('grupo', 'categoria', 'subcategoria')

@admin.register(FactorK)
class FactorKAdmin(admin.ModelAdmin):
    list_display = ('modo_uso', 'naturaleza', 'valor_k')
    list_filter = ('modo_uso', 'naturaleza')

@admin.register(IntensidadCampoE)
class IntensidadCampoEAdmin(admin.ModelAdmin):
    list_display = ('frecuencia_mhz', 'valor_e_mv_m')
    ordering = ('frecuencia_mhz',)