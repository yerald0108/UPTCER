from django.db import models
from django.conf import settings


class Licencia(models.Model):

    ESTADO_VIGENTE   = 'vigente'
    ESTADO_VENCIDA   = 'vencida'
    ESTADO_REVOCADA  = 'revocada'

    ESTADOS = [
        (ESTADO_VIGENTE,  'Vigente'),
        (ESTADO_VENCIDA,  'Vencida'),
        (ESTADO_REVOCADA, 'Revocada'),
    ]

    numero          = models.CharField('Número de licencia', max_length=30, unique=True, editable=False)
    solicitud       = models.OneToOneField(
                        'solicitudes.Solicitud',
                        on_delete=models.PROTECT,
                        related_name='licencia',
                        verbose_name='Solicitud'
                      )
    emitida_por     = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.PROTECT,
                        related_name='licencias_emitidas',
                        verbose_name='Emitida por'
                      )
    estado          = models.CharField('Estado', max_length=20, choices=ESTADOS, default=ESTADO_VIGENTE)
    fecha_emision   = models.DateTimeField('Fecha de emisión', auto_now_add=True)
    fecha_vencimiento = models.DateField('Fecha de vencimiento', null=True, blank=True)
    observaciones   = models.TextField('Observaciones', blank=True)
    motivo_revocacion = models.TextField('Motivo de revocación', blank=True)
    fecha_revocacion  = models.DateTimeField('Fecha de revocación', null=True, blank=True)

    class Meta:
        verbose_name        = 'Licencia'
        verbose_name_plural = 'Licencias'
        ordering            = ['-fecha_emision']

    def __str__(self):
        return f'{self.numero} — {self.get_estado_display()}'

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generar_numero()
        super().save(*args, **kwargs)

    def _generar_numero(self):
        from django.utils import timezone
        año = timezone.now().year
        ultimo = Licencia.objects.filter(
            numero__startswith=f'LIC-{año}'
        ).count()
        return f'LIC-{año}-{str(ultimo + 1).zfill(5)}'

    @property
    def es_vigente(self):
        from django.utils import timezone
        if self.estado != self.ESTADO_VIGENTE:
            return False
        if self.fecha_vencimiento:
            return self.fecha_vencimiento >= timezone.now().date()
        return True

    @property
    def es_temporal(self):
        return self.fecha_vencimiento is not None

    @property
    def clase_badge(self):
        mapa = {
            self.ESTADO_VIGENTE:  'badge-aprobado',
            self.ESTADO_VENCIDA:  'badge-pendiente',
            self.ESTADO_REVOCADA: 'badge-denegado',
        }
        return mapa.get(self.estado, 'badge-info')

    def verificar_vencimiento(self):
        """Actualiza el estado si la licencia temporal venció."""
        from django.utils import timezone
        if (self.estado == self.ESTADO_VIGENTE and
                self.fecha_vencimiento and
                self.fecha_vencimiento < timezone.now().date()):
            self.estado = self.ESTADO_VENCIDA
            self.save(update_fields=['estado'])