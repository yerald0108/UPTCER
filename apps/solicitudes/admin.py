from django.contrib import admin
from .models import Solicitud, HistorialSolicitud


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display    = ('numero', 'flujo', 'estado', 'solicitante', 'fecha_creacion')
    list_filter     = ('flujo', 'estado', 'fecha_creacion')
    search_fields   = ('numero', 'solicitante__nombre', 'solicitante__apellidos')
    ordering        = ('-fecha_creacion',)
    readonly_fields = ('numero', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(HistorialSolicitud)
class HistorialSolicitudAdmin(admin.ModelAdmin):
    list_display  = ('solicitud', 'estado_anterior', 'estado_nuevo', 'usuario', 'fecha')
    list_filter   = ('estado_nuevo',)
    search_fields = ('solicitud__numero',)
    ordering      = ('-fecha',)
    readonly_fields = ('fecha',)