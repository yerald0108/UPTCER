from django.contrib import admin
from .models import Solicitud


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display   = ('numero', 'flujo', 'estado', 'solicitante', 'equipo', 'fecha_creacion')
    list_filter    = ('flujo', 'estado', 'fecha_creacion')
    search_fields  = ('numero', 'solicitante__nombre', 'solicitante__apellidos')
    ordering       = ('-fecha_creacion',)
    readonly_fields = ('numero', 'fecha_creacion', 'fecha_actualizacion')