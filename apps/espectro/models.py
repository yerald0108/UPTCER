from django.db import models
from decimal import Decimal

class FactorFrecuencia(models.Model):
    """Tabla f(t) – factor de frecuencia por banda"""
    banda_min = models.FloatField(help_text="Frecuencia mínima en MHz (inclusive)")
    banda_max = models.FloatField(null=True, blank=True, help_text="Frecuencia máxima en MHz (exclusiva, null para < o >)")
    valor = models.DecimalField(max_digits=6, decimal_places=3)
    descripcion = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['banda_min']

    def __str__(self):
        if self.banda_max is None:
            return f"{self.descripcion} ({self.banda_min} MHz en adelante)"
        return f"{self.banda_min} - {self.banda_max} MHz → {self.valor}"

class FactorServicio(models.Model):
    """Tabla c – factor por tipo de servicio (diferenciado por grupo)"""
    GRUPO_CHOICES = [
        ('1', 'Grupo 1 (CUP)'),
        ('2', 'Grupo 2 (USD)'),
    ]
    grupo = models.CharField(max_length=1, choices=GRUPO_CHOICES)
    categoria = models.CharField(max_length=100)   # ej. "Servicio fijo"
    subcategoria = models.CharField(max_length=200) # ej. "Radioenlaces < 800 MHz"
    valor_c = models.DecimalField(max_digits=12, decimal_places=6)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('grupo', 'subcategoria')

    def __str__(self):
        return f"[Grupo {self.grupo}] {self.subcategoria} = {self.valor_c}"

class FactorK(models.Model):
    """Tabla k – según modo de uso y naturaleza"""
    MODO_CHOICES = [
        ('EXCLUSIVO', 'Exclusivo'),
        ('COMPARTIDO', 'Compartido'),
    ]
    NATURALEZA_CHOICES = [
        ('COMERCIAL', 'Comercial'),
        ('NO_COMERCIAL', 'No Comercial'),
    ]
    modo_uso = models.CharField(max_length=10, choices=MODO_CHOICES)
    naturaleza = models.CharField(max_length=12, choices=NATURALEZA_CHOICES)
    valor_k = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        unique_together = ('modo_uso', 'naturaleza')

    def __str__(self):
        return f"{self.modo_uso} / {self.naturaleza} → {self.valor_k}"

class IntensidadCampoE(models.Model):
    """Tabla E (mV/m) para cálculo de d (distancia)"""
    frecuencia_mhz = models.FloatField(unique=True)
    valor_e_mv_m = models.DecimalField(max_digits=10, decimal_places=6)

    def __str__(self):
        return f"{self.frecuencia_mhz} MHz → {self.valor_e_mv_m} mV/m"
