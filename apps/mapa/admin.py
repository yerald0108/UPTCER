from django.contrib import admin
from .forms import PuntoMapaAdminForm
from .models import PuntoMapa, ImportacionLog


@admin.register(PuntoMapa)
class PuntoMapaAdmin(admin.ModelAdmin):
    form = PuntoMapaAdminForm
    list_display = ('nombre', 'tipo', 'estado', 'latitud', 'longitud')
    list_filter = ('tipo', 'estado')
    search_fields = ('nombre', 'descripcion', 'responsable')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('nombre', 'tipo', 'estado', 'solicitud')
        }),
        ('Ubicación', {
            'fields': ('direccion', 'latitud', 'longitud')
        }),
        ('Información adicional', {
            'fields': (
                'frecuencia_mhz', 'radio_km', 'atributos', 'descripcion',
                'responsable', 'fecha_instalacion', 'ultima_revision'
            )
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ImportacionLog)
class ImportacionLogAdmin(admin.ModelAdmin):
    list_display = ('nombre_archivo', 'fecha', 'estado', 'total_registros', 'creados', 'actualizados', 'errores')
    list_filter = ('estado', 'fecha')
    readonly_fields = ('fecha', 'total_registros', 'creados', 'actualizados', 'errores', 'detalle_errores')
    search_fields = ('nombre_archivo', 'usuario')