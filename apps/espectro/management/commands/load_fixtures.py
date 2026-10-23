from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Carga los datos iniciales de coeficientes'

    def handle(self, *args, **kwargs):
        call_command('loaddata', 'datos_iniciales.json')
        self.stdout.write(self.style.SUCCESS('Datos cargados correctamente'))