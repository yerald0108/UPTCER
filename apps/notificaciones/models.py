from django.db import models
from django.conf import settings
from django.utils import timezone


class Notificacion(models.Model):

    TIPO_SOLICITUD_NUEVA      = 'solicitud_nueva'
    TIPO_DERIVADA_ESPECIALISTA = 'derivada_especialista'
    TIPO_CAMBIO_ESTADO        = 'cambio_estado'
    TIPO_CRITERIO_TECNICO     = 'criterio_tecnico'
    TIPO_GENERAL              = 'general'

    TIPOS = [
        (TIPO_SOLICITUD_NUEVA,       'Nueva solicitud'),
        (TIPO_DERIVADA_ESPECIALISTA, 'Derivada al especialista'),
        (TIPO_CAMBIO_ESTADO,         'Cambio de estado'),
        (TIPO_CRITERIO_TECNICO,      'Criterio técnico emitido'),
        (TIPO_GENERAL,               'General'),
    ]

    destinatario    = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        related_name='notificaciones',
                        verbose_name='Destinatario'
                      )
    tipo            = models.CharField('Tipo', max_length=30, choices=TIPOS, default=TIPO_GENERAL)
    titulo          = models.CharField('Título', max_length=200)
    mensaje         = models.TextField('Mensaje')
    solicitud       = models.ForeignKey(
                        'solicitudes.Solicitud',
                        on_delete=models.CASCADE,
                        null=True,
                        blank=True,
                        related_name='notificaciones',
                        verbose_name='Solicitud relacionada'
                      )
    leida           = models.BooleanField('Leída', default=False)
    fecha_creacion  = models.DateTimeField('Fecha de creación', auto_now_add=True)
    fecha_lectura   = models.DateTimeField('Fecha de lectura', null=True, blank=True)

    class Meta:
        verbose_name        = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering            = ['-fecha_creacion']

    def __str__(self):
        return f'{self.titulo} → {self.destinatario.get_nombre_completo()}'

    def marcar_leida(self):
        if not self.leida:
            self.leida        = True
            self.fecha_lectura = timezone.now()
            self.save(update_fields=['leida', 'fecha_lectura'])

    @property
    def clase_icono(self):
        mapa = {
            self.TIPO_SOLICITUD_NUEVA:       'file-plus',
            self.TIPO_DERIVADA_ESPECIALISTA: 'alert-circle',
            self.TIPO_CAMBIO_ESTADO:         'refresh-cw',
            self.TIPO_CRITERIO_TECNICO:      'clipboard-check',
            self.TIPO_GENERAL:               'bell',
        }
        return mapa.get(self.tipo, 'bell')