from django.db import models
from django.conf import settings


class Solicitud(models.Model):

    # ─── Tipos de flujo ───────────────────────────────────────────────────────
    FLUJO_F43  = 'f43'
    FLUJO_RATS = 'rats'

    FLUJOS = [
        (FLUJO_F43,  'F43 — Solicitud previa a importación'),
        (FLUJO_RATS, 'RATS — Equipo retenido en aduana'),
    ]

    # ─── Estados ──────────────────────────────────────────────────────────────
    ESTADO_BORRADOR    = 'borrador'
    ESTADO_ENVIADA     = 'enviada'
    ESTADO_EN_REVISION = 'en_revision'
    ESTADO_APROBADA    = 'aprobada'
    ESTADO_DENEGADA    = 'denegada'
    ESTADO_CANCELADA   = 'cancelada'

    ESTADOS = [
        (ESTADO_BORRADOR,    'Borrador'),
        (ESTADO_ENVIADA,     'Enviada'),
        (ESTADO_EN_REVISION, 'En revisión'),
        (ESTADO_APROBADA,    'Aprobada'),
        (ESTADO_DENEGADA,    'Denegada'),
        (ESTADO_CANCELADA,   'Cancelada'),
    ]

    # ─── Campos principales ───────────────────────────────────────────────────
    numero          = models.CharField('Número de solicitud', max_length=20, unique=True, editable=False)
    flujo           = models.CharField('Tipo de flujo', max_length=10, choices=FLUJOS)
    estado          = models.CharField('Estado', max_length=20, choices=ESTADOS, default=ESTADO_BORRADOR)

    # Solicitante
    solicitante     = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.PROTECT,
                        verbose_name='Solicitante',
                        related_name='solicitudes'
                      )

    # Equipo
    equipo          = models.ForeignKey(
                        'equipos.Equipo',
                        on_delete=models.PROTECT,
                        verbose_name='Equipo',
                        null=True,
                        blank=True,
                        related_name='solicitudes'
                      )

    # Para equipos no listados en el catálogo
    equipo_no_listado       = models.BooleanField('Equipo no listado en catálogo', default=False)
    equipo_descripcion      = models.TextField('Descripción del equipo (no listado)', blank=True)
    equipo_marca_manual     = models.CharField('Marca (manual)', max_length=100, blank=True)
    equipo_modelo_manual    = models.CharField('Modelo (manual)', max_length=100, blank=True)

    # Documento adjunto (F43 o RATS)
    documento_adjunto       = models.FileField(
                                'Documento adjunto',
                                upload_to='solicitudes/documentos/%Y/%m/',
                                null=True,
                                blank=True
                              )

    # Campos específicos RATS
    numero_rats             = models.CharField('Número RATS', max_length=50, blank=True)
    fecha_retencion         = models.DateField('Fecha de retención', null=True, blank=True)

    # Operador asignado
    operador_asignado       = models.ForeignKey(
                                settings.AUTH_USER_MODEL,
                                on_delete=models.SET_NULL,
                                null=True,
                                blank=True,
                                verbose_name='Operador asignado',
                                related_name='solicitudes_asignadas'
                              )

    # Observaciones
    observaciones_solicitante   = models.TextField('Observaciones del solicitante', blank=True)
    observaciones_operador      = models.TextField('Observaciones del operador', blank=True)
    observaciones_tecnicas      = models.TextField('Criterio técnico', blank=True)

    # Fechas
    fecha_creacion      = models.DateTimeField('Fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('Última actualización', auto_now=True)
    fecha_resolucion    = models.DateTimeField('Fecha de resolución', null=True, blank=True)

    class Meta:
        verbose_name        = 'Solicitud'
        verbose_name_plural = 'Solicitudes'
        ordering            = ['-fecha_creacion']

    def __str__(self):
        return f'{self.numero} — {self.get_flujo_display()} — {self.get_estado_display()}'

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generar_numero()
        super().save(*args, **kwargs)

    def _generar_numero(self):
        from django.utils import timezone
        año = timezone.now().year
        prefijo = 'F43' if self.flujo == self.FLUJO_F43 else 'RAT'
        ultimo = Solicitud.objects.filter(
            numero__startswith=f'{prefijo}-{año}'
        ).count()
        return f'{prefijo}-{año}-{str(ultimo + 1).zfill(4)}'

    # ─── Helpers de estado ────────────────────────────────────────────────────
    @property
    def esta_pendiente(self):
        return self.estado in [self.ESTADO_ENVIADA, self.ESTADO_EN_REVISION]

    @property
    def esta_resuelta(self):
        return self.estado in [self.ESTADO_APROBADA, self.ESTADO_DENEGADA]

    @property
    def es_aprobada(self):
        return self.estado == self.ESTADO_APROBADA

    @property
    def clase_badge(self):
        mapa = {
            self.ESTADO_BORRADOR:    'badge-info',
            self.ESTADO_ENVIADA:     'badge-pendiente',
            self.ESTADO_EN_REVISION: 'badge-revision',
            self.ESTADO_APROBADA:    'badge-aprobado',
            self.ESTADO_DENEGADA:    'badge-denegado',
            self.ESTADO_CANCELADA:   'badge-denegado',
        }
        return mapa.get(self.estado, 'badge-info')