from django.db import models


class CategoriaEquipo(models.Model):
    nombre      = models.CharField('Nombre', max_length=100, unique=True)
    descripcion = models.TextField('Descripción', blank=True)

    class Meta:
        verbose_name        = 'Categoría de equipo'
        verbose_name_plural = 'Categorías de equipos'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


class Equipo(models.Model):

    # ─── Bandas de frecuencia ─────────────────────────────────────────────────
    BANDA_LIBRE        = 'libre'
    BANDA_RESTRINGIDA  = 'restringida'
    BANDA_NO_APLICA    = 'no_aplica'

    BANDAS = [
        (BANDA_LIBRE,       'Banda libre (2.4 / 5.7 GHz)'),
        (BANDA_RESTRINGIDA, 'Frecuencia restringida'),
        (BANDA_NO_APLICA,   'No aplica'),
    ]

    categoria       = models.ForeignKey(
                        CategoriaEquipo,
                        on_delete=models.PROTECT,
                        verbose_name='Categoría',
                        related_name='equipos'
                      )
    nombre          = models.CharField('Nombre del equipo', max_length=200)
    marca           = models.CharField('Marca', max_length=100)
    modelo          = models.CharField('Modelo', max_length=100)
    descripcion     = models.TextField('Descripción técnica', blank=True)
    banda_frecuencia= models.CharField(
                        'Banda de frecuencia',
                        max_length=20,
                        choices=BANDAS,
                        default=BANDA_NO_APLICA
                      )
    requiere_permiso= models.BooleanField('Requiere permiso de importación', default=True)
    activo          = models.BooleanField('Activo en catálogo', default=True)
    fecha_registro  = models.DateTimeField('Fecha de registro', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        verbose_name        = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering            = ['nombre']
        unique_together     = ['marca', 'modelo']

    def __str__(self):
        return f'{self.marca} {self.modelo} — {self.nombre}'

    @property
    def es_banda_libre(self):
        return self.banda_frecuencia == self.BANDA_LIBRE

    @property
    def es_restringido(self):
        return self.banda_frecuencia == self.BANDA_RESTRINGIDA