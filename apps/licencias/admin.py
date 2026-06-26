from django.contrib import admin
from .models import Licencia


@admin.register(Licencia)
class LicenciaAdmin(admin.ModelAdmin):
    list_display    = ('numero', 'solicitud', 'emitida_por', 'estado', 'fecha_emision', 'fecha_vencimiento')
    list_filter     = ('estado',)
    search_fields   = ('numero', 'solicitud__numero')
    ordering        = ('-fecha_emision',)
    readonly_fields = ('numero', 'fecha_emision', 'fecha_revocacion')