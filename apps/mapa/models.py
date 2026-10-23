from django.db import models
from django.utils.translation import gettext_lazy as _


class PuntoMapa(models.Model):
    TIPO_CHOICES = [
        # Radiofaros
        ('RADIOFARO_AEREO', _('Radiofaro Aéreo (VOR/DME/NDB)')),
        ('RADIOFARO_MARITIMO', _('Radiofaro Marítimo')),
        # Antenas
        ('ANTENA_TORRE', _('Antena de Torre')),
        ('ANTENA_PANEL', _('Antena de Panel (sectorial)')),
        ('ANTENA_PARABOLICA', _('Antena Parabólica')),
        ('ANTENA_YAGI', _('Antena Yagi')),
        ('ANTENA_OMNIDIRECCIONAL', _('Antena Omnidireccional')),
        # Estaciones
        ('ESTACION_BASE', _('Estación Base')),
        ('ESTACION_MOVIL', _('Estación Móvil')),
        ('REPETIDORA', _('Repetidora')),
        # Otros
        ('SATELITE', _('Estación Satelital')),
        ('GENERICO', _('Genérico')),
        ('OTRO', _('Otro')),
    ]
    ESTADO_CHOICES = [
        ('ACTIVO', _('Activo')),
        ('INACTIVO', _('Inactivo')),
        ('MANTENIMIENTO', _('En mantenimiento')),
    ]

    nombre = models.CharField(max_length=100, unique=True, verbose_name=_('Nombre'))
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='GENERICO', verbose_name=_('Tipo'))
    latitud = models.FloatField(verbose_name=_('Latitud'), help_text=_('Ej: 23.1136'))
    longitud = models.FloatField(verbose_name=_('Longitud'), help_text=_('Ej: -82.3666'))
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO', verbose_name=_('Estado'))
    atributos = models.JSONField(
        default=dict, blank=True, verbose_name=_('Atributos extra'),
        help_text=_('Almacena datos adicionales en formato JSON (ej: frecuencia, potencia, etc.)')
    )
    descripcion = models.TextField(blank=True, verbose_name=_('Descripción'))
    fecha_instalacion = models.DateField(null=True, blank=True, verbose_name=_('Fecha de instalación'))
    ultima_revision = models.DateField(null=True, blank=True, verbose_name=_('Última revisión'))
    responsable = models.CharField(max_length=100, blank=True, verbose_name=_('Responsable'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Creado'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Actualizado'))

    class Meta:
        verbose_name = _('Punto en el mapa')
        verbose_name_plural = _('Puntos en el mapa')
        ordering = ['tipo', 'nombre']
        indexes = [
            models.Index(fields=['tipo', 'estado']),
            models.Index(fields=['latitud', 'longitud']),
        ]

    def __str__(self):
        return self.nombre

    @property
    def lat_lon(self):
        return f"{self.latitud}, {self.longitud}"

    @property
    def geojson_feature(self):
        """Devuelve el punto en formato GeoJSON Feature."""
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [self.longitud, self.latitud]
            },
            'properties': {
                'id': self.id,
                'nombre': self.nombre,
                'tipo': self.tipo,
                'tipo_display': self.get_tipo_display(),
                'estado': self.get_estado_display(),
                'descripcion': self.descripcion,
                'responsable': self.responsable,
                'fecha_instalacion': self.fecha_instalacion.isoformat() if self.fecha_instalacion else None,
                'ultima_revision': self.ultima_revision.isoformat() if self.ultima_revision else None,
                **self.atributos
            }
        }


class ImportacionLog(models.Model):
    ESTADO_CHOICES = [
        ('EXITOSA', 'Exitosa'),
        ('PARCIAL', 'Parcial con errores'),
        ('FALLIDA', 'Fallida'),
    ]
    archivo = models.FileField(upload_to='importaciones/', blank=True, null=True)
    nombre_archivo = models.CharField(max_length=255)
    total_registros = models.IntegerField(default=0)
    creados = models.IntegerField(default=0)
    actualizados = models.IntegerField(default=0)
    errores = models.IntegerField(default=0)
    detalle_errores = models.JSONField(default=list, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='FALLIDA')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Importación'
        verbose_name_plural = 'Importaciones'

    def __str__(self):
        return f"{self.nombre_archivo} - {self.fecha:%Y-%m-%d %H:%M}"