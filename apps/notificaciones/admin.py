from django.contrib import admin
from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'destinatario', 'tipo', 'leida', 'fecha_creacion')
    list_filter   = ('tipo', 'leida')
    search_fields = ('titulo', 'destinatario__nombre')
    ordering      = ('-fecha_creacion',)
    readonly_fields = ('fecha_creacion', 'fecha_lectura')