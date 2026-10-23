# apps/espectro/enums.py
from django.db import models

class Modulacion(models.TextChoices):
    MQPSK = 'MQPSK', 'MQPSK'
    PSK8 = '8PSK', '8PSK'
    APSK16 = '16APSK', '16APSK'
    APSK32 = '32APSK', '32APSK'